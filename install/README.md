# AI Workroot Install Scripts

`install/` contains user-facing wrapper installers for the Clean Workroot CLI.

These scripts install a user-level `workroot` wrapper. They do not initialize a
Workroot and do not perform first-run setup. After installation, use:

```bash
workroot init --name <name> --directory <directory> --no-native-agent-entry
```
