"""Threshold-robust pure visual embedding and balanced Ward clustering for v7-A1."""
import math
import numpy as np
from PIL import Image

GAUSS_K = np.array([0.06, 0.24, 0.40, 0.24, 0.06], dtype=np.float32)


def _norm(v):
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-8 else v


def _smooth_5(arr):
    # Separable 5-tap Gaussian blur with zero padding.
    pad_x = np.pad(arr, ((0, 0), (2, 2)), mode="constant")
    tmp = (
        pad_x[:, 0:-4] * GAUSS_K[0]
        + pad_x[:, 1:-3] * GAUSS_K[1]
        + pad_x[:, 2:-2] * GAUSS_K[2]
        + pad_x[:, 3:-1] * GAUSS_K[3]
        + pad_x[:, 4:] * GAUSS_K[4]
    )
    pad_y = np.pad(tmp, ((2, 2), (0, 0)), mode="constant")
    return (
        pad_y[0:-4, :] * GAUSS_K[0]
        + pad_y[1:-3, :] * GAUSS_K[1]
        + pad_y[2:-2, :] * GAUSS_K[2]
        + pad_y[3:-1, :] * GAUSS_K[3]
        + pad_y[4:, :] * GAUSS_K[4]
    )


def normalize_canvas32(gray, threshold=128):
    """Fit tight foreground glyph (preserving aspect ratio) centered into a 32x32 uint8 gray tile."""
    ys, xs = np.where(gray < threshold)
    if not len(xs):
        return None
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    crop = gray[y0:y1, x0:x1]
    h, w = crop.shape
    scale = 28.0 / max(h, w)
    nw = max(1, int(round(w * scale)))
    nh = max(1, int(round(h * scale)))
    resized = Image.fromarray(crop.astype(np.uint8)).resize((nw, nh), Image.Resampling.BILINEAR)
    canvas = Image.new("L", (32, 32), 255)
    canvas.paste(resized, ((32 - nw) // 2, (32 - nh) // 2))
    return np.asarray(canvas, dtype=np.uint8), (h, w), (ys - y0, xs - x0)


def embed_glyph(gray, threshold=128):
    """Return a 132-dim L2-normalized pure visual appearance vector and 32x32 gray tile, or (None, None)."""
    res = normalize_canvas32(gray, threshold=threshold)
    if res is None:
        return None, None
    tile32, (h, w), (ry, rx) = res
    # Soft foreground intensity invariant to mild threshold shifts.
    fg = np.clip((255.0 - tile32.astype(np.float32)) / 255.0, 0.0, 1.0)
    mask_bin = (gray < threshold)
    fill_ratio = float(mask_bin[int(np.where(mask_bin)[0].min()):int(np.where(mask_bin)[0].max()) + 1,
                                int(np.where(mask_bin)[1].min()):int(np.where(mask_bin)[1].max()) + 1].mean())

    sm = _smooth_5(fg)
    sm2 = _smooth_5(sm)

    # Block A: 8x8 smoothed density field (64 dims)
    density8 = sm2.reshape(8, 4, 8, 4).mean(axis=(1, 3)).ravel().astype(np.float32)

    # Block B: 4x4 spatial cells x 4 unsigned orientation bins (64 dims)
    p = np.pad(sm, 1, mode="edge")
    gx = (p[1:-1, 2:] - p[1:-1, :-2]) + 0.5 * (p[:-2, 2:] - p[:-2, :-2] + p[2:, 2:] - p[2:, :-2])
    gy = (p[2:, 1:-1] - p[:-2, 1:-1]) + 0.5 * (p[2:, :-2] - p[:-2, :-2] + p[2:, 2:] - p[:-2, 2:])
    mag = np.hypot(gx, gy)
    ang = np.mod(np.arctan2(gy, gx), np.pi) * (4.0 / np.pi)  # [0, 4)
    b0 = np.floor(ang).astype(np.int32) % 4
    b1 = (b0 + 1) % 4
    frac = ang - np.floor(ang)

    hog = np.zeros((4, 4, 4), dtype=np.float32)
    cell_y = np.arange(32)[:, None] // 8
    cell_x = np.arange(32)[None, :] // 8
    for o in range(4):
        w0 = np.where(b0 == o, mag * (1.0 - frac), 0.0)
        w1 = np.where(b1 == o, mag * frac, 0.0)
        tot = w0 + w1
        for cy_i in range(4):
            ym = (cell_y == cy_i)
            for cx_i in range(4):
                hog[cy_i, cx_i, o] = float(tot[ym & (cell_x == cx_i)].sum())
    hog64 = hog.ravel()

    # Block C: 4 coarse appearance globals
    aspect = float(np.clip(math.log((w + 1.0) / (h + 1.0)), -1.5, 1.5) / 1.5)
    cy_off = float((ry.mean() + 0.5) / h - 0.5)
    cx_off = float((rx.mean() + 0.5) / w - 0.5)
    g4 = np.array([aspect, fill_ratio, cy_off, cx_off], dtype=np.float32)

    vec = np.concatenate([_norm(density8) * 1.0, _norm(hog64) * 0.8, _norm(g4) * 0.6]).astype(np.float32)
    return _norm(vec), tile32


def _ward_labels(X, k):
    n = len(X)
    if n <= k:
        return np.arange(n, dtype=np.int32)
    # Initial pairwise squared Euclidean distances
    sq = np.sum(X * X, axis=1, keepdims=True)
    d2 = np.maximum(0.0, sq + sq.T - 2.0 * (X @ X.T)).astype(np.float64)
    # Ward distance between singletons i,j is 0.5 * d2(i,j)
    dist = 0.5 * d2
    np.fill_diagonal(dist, np.inf)
    active = list(range(n))
    members = [[i] for i in range(n)]
    sizes = np.ones(n, dtype=np.float64)
    centroids = X.astype(np.float64).copy()

    # Maintain symmetric active matrix via mask
    alive = np.ones(n, dtype=bool)
    while len(active) > k:
        # Find minimum pair among alive rows/cols
        idx = int(np.argmin(dist))
        i, j = divmod(idx, n)
        if i > j:
            i, j = j, i
        ni, nj = sizes[i], sizes[j]
        nij = ni + nj
        ci, cj = centroids[i], centroids[j]
        new_c = (ni * ci + nj * cj) / nij
        members[i].extend(members[j])
        members[j] = []
        centroids[i] = new_c
        sizes[i] = nij
        alive[j] = False
        active.remove(j)

        # Update Ward distances from merged cluster i to all other alive clusters m using Lance-Williams
        for m in active:
            if m == i:
                dist[i, i] = np.inf
                continue
            nm = sizes[m]
            w_im = (ni * nm / (ni + nm)) * float(np.sum((ci - centroids[m]) ** 2))
            # Wait: compute directly from updated centroid i to avoid Lance-Williams accumulation drift (fast for N<=528)
            val = (nij * nm / (nij + nm)) * float(np.sum((new_c - centroids[m]) ** 2))
            dist[i, m] = dist[m, i] = val
        dist[j, :] = np.inf
        dist[:, j] = np.inf

    labels = np.empty(n, dtype=np.int32)
    for cid, root in enumerate(active):
        for pt in members[root]:
            labels[pt] = cid
    return labels


def _balance_and_clean(X, labels, k, max_size=45):
    n = len(X)
    if k <= 1:
        return np.zeros(n, dtype=np.int32)
    labels = labels.copy()
    for _ in range(12):
        counts = np.bincount(labels, minlength=k)
        centroids = np.array([X[labels == c].mean(axis=0) if counts[c] else X[0] for c in range(k)])
        changed = False

        # Merge tiny singleton buckets (< 2) if there is a large bucket (>= 28) to split
        tiny = [c for c in range(k) if 0 < counts[c] < 2]
        empty = [c for c in range(k) if counts[c] == 0]
        if tiny or empty:
            for c in tiny:
                pts = np.where(labels == c)[0]
                for pt in pts:
                    dists = np.sum((centroids - X[pt]) ** 2, axis=1)
                    dists[c] = np.inf
                    for ec in empty:
                        dists[ec] = np.inf
                    labels[pt] = int(np.argmin(dists))
                changed = True
            counts = np.bincount(labels, minlength=k)
            vacant = [c for c in range(k) if counts[c] == 0]
            for vc in vacant:
                big = int(np.argmax(counts))
                if counts[big] >= 12:
                    idx = np.where(labels == big)[0]
                    sub = X[idx]
                    sub_c = sub.mean(axis=0)
                    _, _, vt = np.linalg.svd(sub - sub_c, full_matrices=False)
                    proj = (sub - sub_c) @ vt[0]
                    move = idx[proj >= np.median(proj)]
                    labels[move] = vc
                    counts = np.bincount(labels, minlength=k)
                    changed = True

        # Cap oversized buckets <= max_size when total capacity permits
        counts = np.bincount(labels, minlength=k)
        centroids = np.array([X[labels == c].mean(axis=0) if counts[c] else X[0] for c in range(k)])
        if counts.max() > max_size and n <= max_size * k:
            for c in range(k):
                while counts[c] > max_size:
                    pts = np.where(labels == c)[0]
                    dists_self = np.sum((X[pts] - centroids[c]) ** 2, axis=1)
                    # Pick farthest point in oversized cluster
                    pt = pts[int(np.argmax(dists_self))]
                    dists_other = np.sum((centroids - X[pt]) ** 2, axis=1)
                    for oc in range(k):
                        if counts[oc] >= max_size or oc == c:
                            dists_other[oc] = np.inf
                    target = int(np.argmin(dists_other))
                    if not np.isfinite(dists_other[target]):
                        break
                    labels[pt] = target
                    counts[c] -= 1
                    counts[target] += 1
                    changed = True
        if not changed:
            break
    return labels


def cluster_cell(X, k, max_size=45):
    """Cluster N vectors into k ordered visual buckets.

    Returns (labels, centroids, medoids, intra_dist, inter_dist).
    """
    n = len(X)
    if n == 0:
        return np.array([], dtype=np.int32), np.empty((0, X.shape[1])), [], 0.0, 0.0
    if k <= 1 or n <= 16:
        c0 = _norm(X.mean(axis=0))
        dmat = np.linalg.norm(X[:, None, :] - X[None, :, :], axis=2)
        med = int(np.argmin(dmat.sum(axis=1)))
        intra = float(np.linalg.norm(X - c0, axis=1).mean())
        return np.zeros(n, dtype=np.int32), c0[None, :], [med], intra, 0.0

    k = min(k, n)
    raw = _ward_labels(X, k)
    labels = _balance_and_clean(X, raw, k, max_size=max_size)

    # Compact active cluster IDs and order deterministically along principal visual axis
    used = sorted(set(labels.tolist()))
    k_eff = len(used)
    centroids = np.array([_norm(X[labels == c].mean(axis=0)) for c in used], dtype=np.float32)

    if k_eff > 1:
        mean_c = centroids.mean(axis=0)
        _, _, vt = np.linalg.svd(centroids - mean_c, full_matrices=False)
        axis = vt[0]
        # Fix sign deterministically using fill_ratio dimension (-3) or sum of density dims
        if float(axis[:64].sum()) < 0:
            axis = -axis
        proj = (centroids - mean_c) @ axis
        order = np.argsort(proj, kind="mergesort")
    else:
        order = np.array([0])

    remap = {used[old_idx]: new_idx for new_idx, old_idx in enumerate(order)}
    ordered_labels = np.array([remap[int(l)] for l in labels], dtype=np.int32)
    ordered_centroids = centroids[order]

    medoids = []
    intra_vals = []
    for cid in range(k_eff):
        pts = np.where(ordered_labels == cid)[0]
        sub = X[pts]
        if len(pts) == 1:
            medoids.append(int(pts[0]))
            intra_vals.append(0.0)
        else:
            dmat = np.linalg.norm(sub[:, None, :] - sub[None, :, :], axis=2)
            medoids.append(int(pts[int(np.argmin(dmat.sum(axis=1)))]))
            intra_vals.append(float(np.linalg.norm(sub - ordered_centroids[cid], axis=1).mean()))

    intra = float(np.mean(intra_vals)) if intra_vals else 0.0
    if k_eff > 1:
        cd = np.linalg.norm(ordered_centroids[:, None, :] - ordered_centroids[None, :, :], axis=2)
        inter = float(cd[np.triu_indices(k_eff, 1)].mean())
    else:
        inter = 0.0
    return ordered_labels, ordered_centroids, medoids, intra, inter
