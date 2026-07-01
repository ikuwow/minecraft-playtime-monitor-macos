# minecraft-playtime-monitor-macos

A small launchd + Python tool that tracks Minecraft Java Edition playtime
on macOS and shows a native notification when daily limits or a curfew
are reached. It never kills the game — it only notifies.

macOS Screen Time does not recognize Minecraft Java's JVM process as a
foreground app, so playtime can't be enforced through Screen Time. This
script fills that gap.

## Components

- `minecraft_playtime_monitor.py` — the monitor script. All settings
  are CLI arguments (`--help` lists them); defaults match the values
  passed by the bundled plist
- `com.ikuwow.minecraft-playtime-monitor.plist` — launchd agent
  definition; passes the settings to the script via
  `ProgramArguments`
- State and logs are written to `~/.local/share/minecraft-playtime-monitor/`

## How it works

launchd wakes the script every minute and the script:

- checks for the Minecraft process with `pgrep -f <pattern>`
  (`--process-pattern`, default `java.*minecraft`)
- if running, adds 1 minute to today's accumulated time
- notifies once when the remaining time matches a threshold
  (`--notify-remaining`)
- once the curfew hour is reached, notifies again every
  `--notify-repeat-interval` accumulated playtime minutes
- once the daily limit is exceeded, notifies again every
  `--notify-repeat-interval` accumulated playtime minutes, including
  elapsed and over-limit minutes

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
(see the Configure section if you have local edits to the plist).
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

Settings are passed to the script as CLI arguments from the plist's
`ProgramArguments`. Run
`~/.local/bin/minecraft_playtime_monitor.py --help` for the full list.
The available flags are:

- `--weekly-limits MON,TUE,WED,THU,FRI,SAT,SUN` — daily limits in
  minutes (default `90,90,90,90,90,120,120`)
- `--curfew-hour H` — hour (0-23) at or after which a curfew
  notification fires (default `22`)
- `--notify-remaining N,N,...` — remaining-minute thresholds for the
  one-shot notification (default `60,10,5,1`)
- `--notify-repeat-interval N` — playtime minutes between repeated
  curfew and over-limit notifications (default `10`)
- `--process-pattern REGEX` — `pgrep -f` pattern to detect the
  Minecraft process (default `java.*minecraft`)

To change values, edit the `ProgramArguments` block in
`com.ikuwow.minecraft-playtime-monitor.plist` (either through the
symlink at `~/Library/LaunchAgents/...` or directly in the clone —
both point to the same file), then reload the agent:

```
launchctl unload ~/Library/LaunchAgents/com.ikuwow.minecraft-playtime-monitor.plist
launchctl load   ~/Library/LaunchAgents/com.ikuwow.minecraft-playtime-monitor.plist
```

Because the install symlinks back into the clone, local edits to the
plist show up as modifications to the tracked file and will conflict
with `git pull`. To keep your local config without committing it,
mark the file as skipped from the index:

```
git update-index --skip-worktree com.ikuwow.minecraft-playtime-monitor.plist
```

To undo:

```
git update-index --no-skip-worktree com.ikuwow.minecraft-playtime-monitor.plist
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
