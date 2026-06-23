# minecraft-playtime-monitor-macos

A small launchd + Python tool that tracks Minecraft Java Edition playtime
on macOS and shows a native notification when daily limits or a curfew
are reached. It never kills the game — it only notifies.

macOS Screen Time does not recognize Minecraft Java's JVM process as a
foreground app, so playtime can't be enforced through Screen Time. This
script fills that gap.

## Components

- `minecraft_playtime_monitor.py` — the monitor script. Settings live at
  the top of the file
- `com.ikuwow.minecraft-playtime-monitor.plist` — launchd agent
  definition
- State and logs are written to `~/.local/share/minecraft-playtime-monitor/`

## How it works

launchd wakes the script every minute and the script:

- checks for the Minecraft process with `pgrep -f java.*minecraft`
- if running, adds 1 minute to today's accumulated time
- notifies once when the remaining time matches a threshold
  (`NOTIFY_REMAINING_MINUTES`)
- notifies once per day when the curfew hour is reached
- notifies once per day when the daily limit is exceeded

## Install

Clone the repository somewhere you keep it long-term (the symlinks
below point back to it), then from the cloned directory:

```
mkdir -p ~/.local/bin ~/Library/LaunchAgents
ln -sfn "$PWD/minecraft_playtime_monitor.py" ~/.local/bin/minecraft_playtime_monitor.py
ln -sfn "$PWD/com.ikuwow.minecraft-playtime-monitor.plist" ~/Library/LaunchAgents/com.ikuwow.minecraft-playtime-monitor.plist
launchctl load ~/Library/LaunchAgents/com.ikuwow.minecraft-playtime-monitor.plist
```

The plist resolves `$HOME` at launch time, so no per-user
substitution is needed. The `ln -sfn` form lets the same commands
be re-run if the clone moves.

## Update

```
git pull
```

The Python script is loaded via the symlink and re-read on every
launchd invocation, so `git pull` is enough for script-only changes
(see the Configure section if you have local edits to the script).
If the plist itself changed, also reload it:

```
launchctl unload ~/Library/LaunchAgents/com.ikuwow.minecraft-playtime-monitor.plist
launchctl load   ~/Library/LaunchAgents/com.ikuwow.minecraft-playtime-monitor.plist
```

## Verify

Confirm the process pattern matches while Minecraft is running:

```
pgrep -fl java.*minecraft
```

Run the script manually and check state:

```
~/.local/bin/minecraft_playtime_monitor.py
cat ~/.local/share/minecraft-playtime-monitor/state.json
```

On first run, approve the notification permission dialog when macOS asks.
Errors are appended to `~/.local/share/minecraft-playtime-monitor/monitor.log`.

## Configure

Edit the constants at the top of `minecraft_playtime_monitor.py`
(either through the symlink at `~/.local/bin/minecraft_playtime_monitor.py`
or directly in the clone — both point to the same file): per-weekday
limits, curfew hour, notification thresholds, and the process pattern.
No launchd reload needed — the script re-reads the file on every
invocation.

Because the install symlinks back into the clone, local edits show up
as modifications to the tracked file and will conflict with `git pull`.
To keep your local config without committing it, mark the file as
skipped from the index:

```
git update-index --skip-worktree minecraft_playtime_monitor.py
```

To undo:

```
git update-index --no-skip-worktree minecraft_playtime_monitor.py
```

## Uninstall

```
launchctl unload ~/Library/LaunchAgents/com.ikuwow.minecraft-playtime-monitor.plist
rm ~/Library/LaunchAgents/com.ikuwow.minecraft-playtime-monitor.plist
rm ~/.local/bin/minecraft_playtime_monitor.py
rm -rf ~/.local/share/minecraft-playtime-monitor
```

## Known limitations

- 1-minute sampling — up to a 1-minute margin of error
- Counts do not advance while the Mac is asleep (launchd doesn't fire)
- Notification-only; stopping is left to the user

## License

MIT
