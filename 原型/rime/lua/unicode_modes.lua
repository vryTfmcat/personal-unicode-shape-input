-- Independent exact-match dictionaries, source merging and standalone left Shift.
local M = {}
local layers = {
  {"personal", "unicode_personal", "收藏"},
  {"block", "unicode_block", "区块"},
  {"shape", "unicode_shape", "全形"},
  {"chinese", "unicode_chinese", "中文"},
  {"extended", "unicode_extended", "中文扩展"},
}
M.translator = {}
function M.translator.init(env)
  env.tables = {}
  for _, item in ipairs(layers) do
    if env.engine.schema.config:get_bool(item[2] .. "/available") then
      env.tables[item[1]] = Component.Translator(env.engine, "", "table_translator@" .. item[2])
    end
  end
end
function M.translator.func(input, segment, env)
  local ctx = env.engine.context
  local rows, order = {}, {}
  for _, item in ipairs(layers) do
    local layer, option, label = item[1], item[2], item[3]
    local enabled = ctx:get_option(option)
    if layer == "extended" then enabled = enabled and ctx:get_option("unicode_chinese") end
    local min_shape = env.engine.schema.config:get_int("unicode_shape/min_code_length") or 2
    if layer == "shape" and (#input < min_shape or #input > 4) then enabled = false end
    if enabled and env.tables[layer] then
      local translation = env.tables[layer]:query(input, segment)
      if translation then
        for cand in translation:iter() do
          -- Exact Unicode sequence identity. Never merge lookalikes or compatibility forms.
          if not rows[cand.text] then rows[cand.text] = {}; table.insert(order, cand.text) end
          local sources = rows[cand.text]
          local exists = false
          for _, old in ipairs(sources) do if old == label then exists = true end end
          if not exists then table.insert(sources, label) end
        end
      end
    end
  end
  for _, text in ipairs(order) do
    yield(Candidate("unicode_modes", segment.start, segment._end, text, table.concat(rows[text], "+")))
  end
end

M.processor = {}
local updating = false
local resume_shift = nil
local function display_schema(ctx)
  local mask = (ctx:get_option("unicode_block") and 1 or 0)
    + (ctx:get_option("unicode_shape") and 2 or 0)
    + (ctx:get_option("unicode_personal") and 4 or 0)
  return mask == 1 and "personal_unicode_modes" or "personal_unicode_modes_" .. mask
end
local function sync_icon(env)
  local engine, ctx = env.engine, env.engine.context
  local target = display_schema(ctx)
  if updating or engine.schema.schema_id == target then return false end
  -- The same Context survives ApplySchema, but Rime clears its composition.
  -- Restore raw input, caret and English state without committing any character.
  local input, caret, ascii = ctx.input, ctx.caret_pos, ctx:get_option("ascii_mode")
  resume_shift = {env.left_pending, env.left_used}
  updating = true
  engine:apply_schema(Schema(target))
  ctx:set_option("ascii_mode", ascii)
  ctx.input = input
  ctx.caret_pos = caret
  updating = false
  resume_shift = nil
  return true
end
function M.processor.init(env)
  env.left_pending = resume_shift and resume_shift[1] or false
  env.left_used = resume_shift and resume_shift[2] or false
  env.preference_path = rime_api.get_user_data_dir() .. "/unicode_modes.preferences.yaml"
  env.preferences = Config(env.preference_path)
  local ctx = env.engine.context
  -- Explicitly choosing a display variant in the Rime menu selects that mode.
  -- The common entry retains saved preferences; internal reloads already saved them.
  local chosen = not updating and tonumber(env.engine.schema.schema_id:match("^personal_unicode_modes_(%d)$"))
  local bits = {block = 1, shape = 2, personal = 4}
  for _, item in ipairs(layers) do
    local saved = env.preferences:get_bool(item[2])
    if saved == nil then saved = item[1] == "block" end
    if chosen and bits[item[1]] then saved = math.floor(chosen / bits[item[1]]) % 2 == 1 end
    ctx:set_option(item[2], saved)
  end
  for _, item in ipairs(layers) do env.preferences:set_bool(item[2], ctx:get_option(item[2])) end
  env.preferences:save_to_file(env.preference_path)
  env.option_connection = ctx.option_update_notifier:connect(function(context, name)
    for _, item in ipairs(layers) do
      if name == item[2] then
        for _, entry in ipairs(layers) do
          env.preferences:set_bool(entry[2], context:get_option(entry[2]))
        end
        env.preferences:save_to_file(env.preference_path)
        sync_icon(env)
        return
      end
    end
  end)
end
function M.processor.fini(env)
  if env.option_connection then env.option_connection:disconnect() end
end
function M.processor.func(key, env)
  local ctx = env.engine.context
  -- On initial load, saved preferences may differ from the entry schema icon.
  -- Re-dispatch through the new processors and stop traversing the old vector.
  if sync_icon(env) then
    return env.engine:process_key(key) and 1 or 0
  end
  local left = key.keycode == 0xffe1
  if left and not key:release() then
    if not key:ctrl() and not key:alt() and not key:super() then
      -- Repeat keydown must not reset the used flag.
      if not env.left_pending then env.left_pending, env.left_used = true, false end
    else env.left_used = true end
    return 2
  end
  if left and key:release() then
    local toggle = env.left_pending and not env.left_used and not key:ctrl() and not key:alt() and not key:super()
    env.left_pending, env.left_used = false, false
    if not toggle then return 2 end
    local b, s, p = ctx:get_option("unicode_block"), ctx:get_option("unicode_shape"), ctx:get_option("unicode_personal")
    local nb, ns, np
    if b and not s and not p then nb, ns, np = false, true, false
    elseif s and not b and not p then nb, ns, np = false, false, true
    elseif p and not b and not s then nb, ns, np = true, true, true
    elseif b and s and p then nb, ns, np = true, false, false
    else nb, ns, np = true, true, true end
    updating = true
    ctx:set_option("unicode_block", nb); ctx:set_option("unicode_shape", ns); ctx:set_option("unicode_personal", np)
    updating = false
    sync_icon(env)
    ctx:refresh_non_confirmed_composition()
    return 1
  end
  if env.left_pending and not key:release() then env.left_used = true end
  return 2
end
return M
