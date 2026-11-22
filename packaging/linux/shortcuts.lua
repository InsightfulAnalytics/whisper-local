-- Whisper Local: Hyprland bindings, installed to ~/.config/whisper-local/.
-- Omarchy loads this file while whisper-local is its dictation backend
-- (omarchy-default-dictation), and stops loading it when another backend is
-- chosen. Omarchy already routes its own dictation keys (Alt+Space toggles,
-- holding Right Alt talks) to omarchy-dictation-whisper-local; this file adds
-- the Superwhisper keys: Ctrl+Alt+Space toggles and Escape cancels.
if package.loaded["whisper-local.shortcuts"] then return end
package.loaded["whisper-local.shortcuts"] = true

-- One long-lived `whisper-local-ctl --bridge` carries every key press to the
-- app's control socket, so Escape (seen on every press, below) costs a pipe
-- write rather than a new process.
--
-- The shell io.popen starts must exit at once, so it runs the bridge in the
-- background (`<&0` keeps the pipe as its stdin). A reload closes this handle,
-- and closing a popen handle waits for that shell. If the shell were the
-- bridge, Hyprland's main thread would wait for the bridge to read end-of-file,
-- which never comes while any process Hyprland started since holds a copy of
-- the pipe (they all inherit it): the whole desktop froze that way. The next
-- bridge retires the old one instead.
local bridge = io.popen("whisper-local-ctl --bridge <&0 &", "w")
if bridge then
  bridge:setvbuf("no")
end

local function send(command)
  if bridge then
    local ok = pcall(function()
      bridge:write(command .. "\n")
      bridge:flush()
    end)
    if ok then
      return
    end
    bridge = nil
  end
  -- No bridge (it failed to start or died): one process per command still works.
  hl.dispatch(hl.dsp.exec_cmd("whisper-local-ctl " .. command))
end

hl.bind("CTRL + ALT + SPACE", function() send("toggle") end,
  { description = "Whisper Local: toggle dictation" })

-- Escape still reaches the focused app (non-consuming), as with Superwhisper.
-- The app ignores cancel unless it is recording.
hl.bind("Escape", function() send("cancel") end,
  { description = "Whisper Local: cancel dictation", non_consuming = true, ignore_mods = true })

-- The recording pill (level_overlay.py) is an XWayland window. Hyprland would
-- focus it when it appears, and the paste would then land in the pill.
hl.window_rule({
  match = { xwayland = true, title = "^Whisper Local overlay$" },
  float = true,
  pin = true,
  no_focus = true,
  no_initial_focus = true,
  decorate = false,
  border_size = 0,
  no_shadow = true,
  no_blur = true,
  no_anim = true,
})

-- The edge glow (a click-through overlay at the bottom of the focused window)
-- fades and ripples by itself, so Hyprland's layer animation is turned off.
hl.layer_rule({ match = { namespace = "^whisper-local-glow$" }, no_anim = true })

-- Omarchy stops push-to-talk with a release binding on Right Alt, and Hyprland
-- skips a release binding once another key or mouse button was released during
-- the hold. Report Right Alt's own release too; a stop the app already handled
-- is a no-op. Hyprland's Lua key event uses XKB codes: evdev 100 + 8.
local RIGHT_ALT = 100 + 8
hl.on("input.keyboard.key", function(code, _, state)
  if code == RIGHT_ALT and state == 0 then
    send("stop")
  end
end)
