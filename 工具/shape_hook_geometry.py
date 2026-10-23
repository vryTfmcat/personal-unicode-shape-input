"""Certify straight-armed junctions without deleting a genuine curved hook."""
import numpy as np

from shape_experiment_features import crossing_topology


def straight_armed_junction(f):
    if len(f['parts']) != 1 or f['holes'] or len(f['junctionObjects']) != 1:
        return False
    sk = crossing_topology(f['body'])['skeleton']
    p = np.pad(sk, 1)
    ns = [p[:-2, 1:-1], p[:-2, 2:], p[1:-1, 2:], p[2:, 2:],
          p[2:, 1:-1], p[2:, :-2], p[1:-1, :-2], p[:-2, :-2]]
    transitions = sum((~ns[i] & ns[(i + 1) % 8]).astype('uint8') for i in range(8))
    ends = np.argwhere(sk & (transitions == 1))[:, ::-1].astype(float)
    if len(ends) < 3:
        return False
    box = f['junctionObjects'][0]['coreBbox']
    centre = (np.array(box[:2]) + np.array(box[2:]) - 1) / 2
    points = np.argwhere(sk)[:, ::-1] - centre
    rays = ends - centre
    length2 = (rays ** 2).sum(axis=1)
    if length2.min() < 16:
        return False
    t = np.clip(points @ rays.T / length2, 0, 1)
    distance = ((points[:, None, :] - t[:, :, None] * rays[None, :, :]) ** 2).sum(axis=2).min(axis=1)
    return bool(distance.max() <= 2.0 ** 2)
