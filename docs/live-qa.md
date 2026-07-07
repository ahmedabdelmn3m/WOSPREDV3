# WOSPREDV3 Live QA

## Active Frontend

Deploy the `frontend` folder on Vercel.

Recommended Vercel settings:

- Framework Preset: `Other`
- Root Directory: `frontend`
- Build Command: leave empty
- Output Directory: `.`

The root-level `index.html`, `app.js`, and `config.js` are older duplicated files. The `frontend/root_*` files are also legacy snapshots. Do not use these as production unless Vercel is intentionally reconfigured and the duplicate files are cleaned up.

## API URL

The active browser config is `frontend/config.js`.

Default Railway API URL:

```text
https://wospredv3-production.up.railway.app
```

To override it from the browser, open the main app, click `API Settings`, paste the Railway URL, and save. The value is stored in `localStorage` under `wos_api_url`.

The QA page also has a URL input for quick testing. It uses the same `localStorage` key.

## Railway CORS

The backend allows localhost for development and the `wospredv3*.vercel.app` Vercel domain family by default. For a custom domain or a renamed Vercel project, set this Railway variable to the exact allowed frontend origins:

```text
CORS_ORIGINS=https://your-vercel-domain.vercel.app,https://your-custom-domain.com
```

## After Every Codex Change

1. Push the change to GitHub.
2. Wait for Railway and Vercel deployments to finish.
3. Open the Vercel app from the deployed `frontend` folder.
4. Open `qa.html` from the app header or visit `/qa.html`.
5. Confirm these checks show `PASS`:
   - Current frontend version/source
   - Current API URL
   - `GET /`
   - `GET /model-accuracy`
   - `POST /predict-outcome`
   - `POST /reverse-optimize`
   - `POST /formation/optimize`
   - CORS/API reachability errors
6. Return to the Battle Predictor and run the normal prediction and formation actions.

If a browser check fails with a CORS or network-style error, first confirm the Railway URL is correct in `API Settings`, then confirm Railway has the correct `CORS_ORIGINS` for the Vercel domain.
