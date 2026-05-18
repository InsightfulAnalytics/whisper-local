#!/usr/bin/env pwsh
# Companion script for recording the README demo GIF.
# Opens a clean Notepad, positions it on the centre of screen, and prints
# the script you should speak. Start your GIF recorder over the Notepad
# window, run this script, then perform the dictation.

$ErrorActionPreference = 'Stop'

Add-Type @'
using System;
using System.Runtime.InteropServices;
public class Win {
    [DllImport("user32.dll")] public static extern IntPtr FindWindow(string a, string b);
    [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr h, int x, int y, int w, int t, bool r);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern int GetSystemMetrics(int n);
}
'@

Write-Host @"

==============================================
   Whisper Local - Demo Recording Helper
==============================================

This script:
  1. Opens Notepad
  2. Centres it on your screen at a good size for GIF capture
  3. Prints the demo script for you to read out loud
  4. Counts down 5 seconds so you can start your screen recorder

After the countdown, hold Ctrl+Win and speak the line below.

"@ -ForegroundColor Cyan

$line = "Hold Ctrl+Win, speak this sentence, then release - the quick brown fox jumps over the lazy dog period"

Write-Host "Suggested line:" -ForegroundColor Yellow
Write-Host "  $line" -ForegroundColor White
Write-Host ""
Write-Host "Press Enter when your screen recorder is ready..." -ForegroundColor Gray
Read-Host

Start-Process notepad.exe
Start-Sleep -Seconds 1

$hwnd = [Win]::FindWindow($null, "Untitled - Notepad")
if (-not $hwnd -or $hwnd -eq [IntPtr]::Zero) {
    $hwnd = [Win]::FindWindow("Notepad", $null)
}

if ($hwnd -and $hwnd -ne [IntPtr]::Zero) {
    $screenW = [Win]::GetSystemMetrics(0)
    $screenH = [Win]::GetSystemMetrics(1)
    $w = 720
    $h = 360
    $x = ($screenW - $w) / 2
    $y = ($screenH - $h) / 2 - 80
    [void][Win]::MoveWindow($hwnd, [int]$x, [int]$y, $w, $h, $true)
    Start-Sleep -Milliseconds 200
    [void][Win]::SetForegroundWindow($hwnd)
}

Write-Host ""
Write-Host "Notepad ready. Counting down..." -ForegroundColor Yellow

for ($i = 5; $i -ge 1; $i--) {
    Write-Host "  $i" -ForegroundColor Yellow
    Start-Sleep -Seconds 1
}

Write-Host ""
Write-Host "GO! Hold Ctrl+Win and speak now." -ForegroundColor Green
Write-Host ""
Write-Host "When done recording:" -ForegroundColor Cyan
Write-Host "  1. Stop your screen recorder" -ForegroundColor White
Write-Host "  2. Trim to ~6 seconds" -ForegroundColor White
Write-Host "  3. Save as docs\demo.gif (aim for under 2 MB)" -ForegroundColor White
Write-Host "  4. Uncomment the demo line in README.md" -ForegroundColor White
Write-Host ""
