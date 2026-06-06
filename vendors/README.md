# Vendor presets

A **preset** is a `vendors/<brand>/` subfolder containing one or both of:

- `credentials.txt`: a list of `user:password` pairs to try.
- `paths.txt`: a list of RTSP paths to probe.

The folder name is the preset name you reference in `vendors_presets` in your `config.yaml`.

## Layout

```
vendors/
├── ubiquiti/
│   ├── credentials.txt
│   └── paths.txt
├── hikvision/
│   ├── credentials.txt
│   └── paths.txt
└── mybrand/                 # drop your own here
    ├── credentials.txt
    └── paths.txt
```

Both files are optional, but a preset must contain at least one of them.

## `credentials.txt` format

Hydra / Medusa / John the Ripper convention: one `user:password` per line, **split on the first `:`** so passwords may contain colons. Empty password is supported (line ends right after `:`). Lines starting with `#` and blank lines are ignored. Dense format that scales to millions of pairs.

```
# vendors/mybrand/credentials.txt
admin:admin
admin:hunter2
root:p4ss:w0rd        # password contains ':', that's fine
admin:                # empty password
```

## `paths.txt` format

One path per line, optionally followed by a TAB and a human-readable label. Without a label, one is auto-generated as `<vendor> <path>`. Lines starting with `#` and blank lines are ignored.

```
# vendors/mybrand/paths.txt
/stream/main	Main camera
/stream/sub	Sub stream
/snapshot
```

TAB is used (not space or `:`) because labels routinely contain spaces and paths can legally contain `:`. TAB is the only separator with zero collision risk against either field.

## Enabling a preset

In your `config.yaml`, set the preset name to `true` under `vendors_presets`:

```yaml
instances:
  - name: "Test"
    host: 192.168.1.42
    username: alice
    password: secret
    vendors_presets:
      mybrand: true
```

Activating a preset does two things at once:

1. Restricts the path catalog to that vendor's paths.
2. Tries that vendor's credentials in addition to the per-instance `username` / `password`.

## Local-only presets

Any subfolder of `vendors/` other than the built-in presets is git-ignored by default. Drop your private vendor folder anywhere under `vendors/` and it stays local.
