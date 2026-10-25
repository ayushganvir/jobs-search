#!/usr/bin/env python3
"""tabjump.py <tab_id> [url]: bring one Chrome tab to the front (macOS AppleScript).
Finds the tab by Chrome's tab id (the same id the Control_Chrome tools report); if that id is gone (Chrome restarted),
falls back to the first tab whose URL starts with <url> (query string ignored); if none, opens <url> in a new tab.
Then closes the helper tab that called /go on the dashboard server. Prints what it did."""
import subprocess, sys

SCRIPT = r'''
on run argv
  set wantId to item 1 of argv
  set wantUrl to item 2 of argv
  tell application "Google Chrome"
    set found to false
    repeat with w in windows
      set i to 0
      repeat with t in tabs of w
        set i to i + 1
        if (id of t as text) is wantId then
          set active tab index of w to i
          set index of w to 1
          set found to true
          exit repeat
        end if
      end repeat
      if found then exit repeat
    end repeat
    if not found and wantUrl is not "" then
      repeat with w in windows
        set i to 0
        repeat with t in tabs of w
          set i to i + 1
          if (URL of t) starts with wantUrl then
            set active tab index of w to i
            set index of w to 1
            set found to true
            exit repeat
          end if
        end repeat
        if found then exit repeat
      end repeat
    end if
    set result_ to "focused"
    if not found then
      if wantUrl is "" then return "not found"
      tell window 1 to make new tab with properties {URL:wantUrl}
      set result_ to "opened"
    end if
    repeat with w in windows
      repeat with t in (tabs of w)
        if (URL of t) contains "127.0.0.1:8787/go" then close t
      end repeat
    end repeat
    activate
    return result_
  end tell
end run
'''

def jump(tab_id, url=""):
    url = (url or "").split("?")[0] if "myworkdayjobs" not in (url or "") else (url or "")
    r = subprocess.run(["osascript", "-", str(tab_id or ""), url], input=SCRIPT, capture_output=True, text=True, timeout=20)
    return (r.stdout or r.stderr).strip()

if __name__ == "__main__":
    print(jump(sys.argv[1] if len(sys.argv) > 1 else "", sys.argv[2] if len(sys.argv) > 2 else ""))
