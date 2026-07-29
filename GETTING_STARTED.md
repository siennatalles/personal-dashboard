# Getting Started — zero assumed knowledge

This walks through everything from "I have this folder" to "my real Apple
Calendar/Gmail/Canvas/weather data is showing up." Do the steps in order —
each one builds on the last. It's fine to stop after any step and come back
later.

## Part 1: See it running (no accounts needed yet)

**1. Open Terminal.** On a Mac: press `Cmd + Space`, type `Terminal`, hit
Enter. A black/white window with text opens — that's it, that's Terminal.

**2. Move into the project folder.** Type `cd ` (with a trailing space),
then drag the `personal-dashboard` folder from Finder directly into the
Terminal window — it'll paste the full path in automatically — then press
Enter. You should see the prompt change to show you're inside the folder.

**3. Install the pieces it needs.** Copy-paste this exactly and press Enter:
```
pip install -r requirements.txt
```
This downloads the code libraries the project depends on. Takes a minute or
two. Some yellow warning text is normal — only worry about lines starting
with `ERROR`.

**4. Start it.** Copy-paste and press Enter:
```
uvicorn app.main:app --reload
```
You'll see some text end with `Application startup complete.` — leave this
Terminal window open and running.

**5. Look at it.** Open a web browser, go to `http://127.0.0.1:8000`. You
should see the dashboard with made-up sample data — a fake calendar, fake
emails, fake assignments. This is "demo mode," and it proves everything
works before you connect anything real.

To stop it later: click back into that Terminal window and press `Ctrl + C`.

## Part 2: Understand the .env file (this is the only "connecting" step)

Every real account you connect (Apple, Gmail, Canvas) works the same way:
you get a password/token/ID from that service, and you paste it into one
plain text file called `.env`. The app reads that file every time it starts
and uses whatever's in there.

**Create it once:** in Terminal (same window, or open a new one and `cd`
back into the folder), run:
```
cp .env.example .env
```
This copies the template into a real file called `.env`. Now open `.env` in
any text editor (TextEdit works: right-click the file in Finder → Open With
→ TextEdit) — you'll see the same categories as below, each with blank
spots to fill in.

You do **not** need to fill in every service at once. Do one at a time,
save the file, restart the app (`Ctrl+C` then run the `uvicorn` command
again), and check the dashboard — you'll see that one section switch from
demo data to your real data while everything else stays in demo mode.

## Part 3: Connect each service (easiest first)

### Apple Calendar — easiest, do this one first
1. On your iPhone: **Settings → [your name at the top] → Sign-In & Security
   → App-Specific Passwords → Generate Password**. (If you don't see this
   option, you need 2-Factor Authentication turned on first, same menu.)
2. Give it any label (e.g. "dashboard"), tap Create. You'll see a password
   that looks like `abcd-efgh-ijkl-mnop`.
3. In your `.env` file, find these two lines and fill them in:
   ```
   APPLE_ID=your_actual_icloud_email@icloud.com
   APPLE_APP_SPECIFIC_PASSWORD=abcd-efgh-ijkl-mnop
   ```

### Canvas — also easy
1. Log into your school's Canvas website (in a browser, like normal).
2. Click **Account** (left sidebar) → **Settings**.
3. Scroll to **Approved Integrations** → click **+ New Access Token**.
4. Give it a purpose (e.g. "dashboard"), click **Generate Token**. Copy the
   long string it shows you — you only get to see it once.
5. In `.env`:
   ```
   CANVAS_BASE_URL=https://yourschool.instructure.com
   CANVAS_ACCESS_TOKEN=paste_the_long_token_here
   ```
   (`CANVAS_BASE_URL` is just your school's Canvas web address — whatever
   you type into your browser to reach Canvas, minus anything after `.com`.)

### Gmail — one extra step
1. Go to https://myaccount.google.com/security and make sure **2-Step
   Verification** is turned on (turn it on if not — it'll text/prompt your
   phone).
2. Go to https://myaccount.google.com/apppasswords.
3. Type a name like "dashboard", click Create. Copy the 16-character
   password it shows you.
4. In `.env`:
   ```
   GMAIL_ADDRESS=your_actual_gmail@gmail.com
   GMAIL_APP_PASSWORD=the16characterpassword
   ```
   (Type it with no spaces even if Google shows it with spaces.)

### Weather — easiest of all, no account needed
1. In `.env`, find `WEATHER_LOCATION` and set it to your city:
   ```
   WEATHER_LOCATION=St. Louis, MO
   ```
   That's it — no signup, no key. If the city name doesn't match, you can
   also use exact coordinates like `WEATHER_LOCATION=38.63,-90.2`.

### AI daily summary — optional, skip if you don't want it
Powers the short narrative at the top of the dashboard. Without this it
falls back to a simple non-AI summary — nothing breaks either way.
1. Go to https://console.anthropic.com, create an API key.
2. In `.env`:
   ```
   ANTHROPIC_API_KEY=paste_the_key_here
   ```

## Part 4: Turn off demo mode

Once you've filled in at least one service, open `.env` and change the very
first line from:
```
DEMO_MODE=true
```
to:
```
DEMO_MODE=false
```
Save the file, stop the server (`Ctrl+C` in Terminal) and start it again
(`uvicorn app.main:app --reload`), then refresh the dashboard in your
browser. Whatever you filled in should now show your real data; anything
you left blank will keep showing demo data for just that section — nothing
breaks.

## If something goes wrong

Scroll to the bottom of the dashboard page — there's a small status row
showing each source, whether it succeeded, and (if not) the actual error
message. That's the first place to look; the error text is usually specific
enough to tell you what's wrong (wrong password, expired token, etc.).
