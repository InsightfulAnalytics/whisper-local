# window_glow.py (Linux)
# Paints the focused window's border for the WindowGlow recording indicator.
# A named Hyprland window rule gives every window carrying the tag
# "whisper-local-glow" the current gradient; each frame re-registers the rule
# with new colours, and the tag follows focus. Clearing drops the tag, so the
# window returns to the theme's border. (set_prop would be simpler, but its
# override can't be undone: "unset" leaves a gradient border blank.) A thicker
# border comes from a second rule registered once per glow: the window resizes
# when the glow starts and ends, never per frame.

from . import hyprland

_TAG = 'whisper-local-glow'
_RULE = 'whisper-local-glow'
_SIZE_RULE = 'whisper-local-glow-size'
# The tagged window's address lives in Lua, so focus moves can be followed.
_GLOBAL = 'whisper_local_glow_address'
_SIZED = 'whisper_local_glow_sized'

_PAINT_LUA = """
if {border_size} > 0 and not {sized} then
  hl.window_rule({{ name = "{size_rule}", match = {{ tag = "{tag}" }}, border_size = {border_size} }})
  {sized} = true
end
hl.window_rule({{ name = "{rule}", match = {{ tag = "{tag}" }}, border_color = "{gradient}" }})
local window = hl.get_active_window()
local address = window and window.address
local previous = {glob}
if previous ~= address then
  if previous then
    pcall(hl.dispatch, hl.dsp.window.tag({{ window = "address:" .. previous, tag = "-{tag}" }}))
  end
  if address then
    pcall(hl.dispatch, hl.dsp.window.tag({{ window = "address:" .. address, tag = "+{tag}" }}))
  end
  {glob} = address
end
"""

_CLEAR_LUA = f"""
if {_GLOBAL} then
  pcall(hl.dispatch, hl.dsp.window.tag({{ window = "address:" .. {_GLOBAL}, tag = "-{_TAG}" }}))
  {_GLOBAL} = nil
end
hl.window_rule({{ name = "{_RULE}", enabled = false }})
if {_SIZED} then
  hl.window_rule({{ name = "{_SIZE_RULE}", enabled = false }})
  {_SIZED} = nil
end
"""


def is_supported() -> bool:
    return hyprland.is_available()


# gradient: Hyprland gradient syntax, built by window_glow.gradient().
# border_size: border width in pixels while glowing; 0 keeps the theme's.
def paint(gradient: str, border_size: int = 0):
    hyprland.eval_lua(_PAINT_LUA.format(rule=_RULE, size_rule=_SIZE_RULE, tag=_TAG, glob=_GLOBAL,
                                        sized=_SIZED, gradient=gradient, border_size=int(border_size)))


def clear():
    hyprland.eval_lua(_CLEAR_LUA)
