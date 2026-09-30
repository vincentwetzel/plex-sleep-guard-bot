# Discord application setup

This guide creates a bot application, stores its credential locally, and installs it to a test server. Portal labels can change; use the official Discord guides linked below if the interface has moved.

## 1. Create the application and bot token

1. Open the [Discord Developer Portal](https://discord.com/developers/applications) and choose **New Application**.
2. Name the application, accept the developer terms, and create it.
3. On **General Information**, copy the **Application ID** into `DISCORD_APPLICATION_ID` in your project `.env` file.
4. Open **Bot**. Use **Reset Token** to generate a bot token, then copy it directly into `DISCORD_BOT_TOKEN` in `.env`.
5. Save `.env` locally. Do not paste the token into source control, chat, screenshots, logs, or support messages. If it is lost or exposed, reset it in the portal and update `.env`.

The Application ID is the only Discord ID this project needs to configure. It is used for command registration and diagnostics. Global command sync means no test server ID is required. The official [getting started guide](https://docs.discord.com/developers/quick-start/getting-started) describes application setup and credentials. See Discord's [bot token guidance](https://support-dev.discord.com/hc/en-us/articles/6470840524311-Why-can-t-I-copy-my-bot-s-token) if the token is not visible.

## 2. Choose installation scopes and permissions

On the portal's **Installation** page, enable **Guild Install** and use the generated install link. Select these scopes for the guild installation:

- `bot`
- `applications.commands`

The bot does not need channel permissions for its current private slash-command responses. Leave the permissions selection empty. The bot also does not need privileged Gateway intents such as Message Content, Members, or Presence. It requests only the non-privileged `guilds` intent.

Discord's [installation guide](https://docs.discord.com/developers/quick-start/getting-started#adding-scopes-and-bot-permissions) explains scopes and permissions. The [application commands guide](https://docs.discord.com/developers/interactions/application-commands) describes slash-command registration and use.

## 3. Install it to a test server

1. Choose a private server where you have permission to add applications.
2. Open the generated install link and choose **Add to server**.
3. Select the test server, review the scopes and permissions, and authorize.

No server ID is needed in the bot configuration. Discord Developer Mode and copying user/server IDs are unnecessary for the current features.

## 4. Run the bot and verify commands

Install the project and start it on the Windows machine that should stay awake. Confirm it is online in the server, then run `/stay-awake` with an integer duration within `STAY_AWAKE_MAX_MINUTES`. Responses are private. Use `/guard-notifications enabled:false` to opt out of the expiry DM, or `enabled:true` to opt in again.

Application commands sync globally at startup and may take time to appear. The bot must remain running and connected to Discord to receive a command. It cannot wake a sleeping PC. The Windows request prevents automatic idle sleep only; it does not inhibit the display or prevent explicit sleep/shutdown or power loss.
