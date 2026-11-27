local compact, expanded = "unicode_shape_v7_a1", "unicode_shape_v7_a1_expanded"
return function(key, env)
  local engine = env.engine
  local ctx = engine.context
  local keycode = key.keycode
  if engine.schema.schema_id == expanded and ctx:has_menu()
      and not key:ctrl() and not key:alt() and not key:super() and not key:shift()
      and ((keycode >= 0x30 and keycode <= 0x39) or (keycode >= 0xffb0 and keycode <= 0xffb9)) then
    return 1
  end
  local letter = key.keycode == 0x45 or key.keycode == 0x65
  if not letter or not key:ctrl() or not key:shift() or key:alt() or key:super() or key:release() or not ctx:has_menu() then
    return 2
  end
  local input, caret = ctx.input, ctx.caret_pos
  local target = engine.schema.schema_id == compact and expanded or compact
  engine:apply_schema(Schema(target))
  ctx.input, ctx.caret_pos = input, caret
  return 1
end
