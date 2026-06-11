# نشر موسوعة الرجال برابط عام — دليل خطوة بخطوة

The app folder is self-contained once `rijal_public.db` is built. Two good free options:

## Option A (recommended): Hugging Face Spaces — handles the large DB easily
1. Build the public DB (from `Dirayah3/`):  `python build_public_db.py`
   → creates `app/rijal_public.db` (~250 MB; the app auto-detects it).
2. Create a free account at https://huggingface.co → **New Space** →
   SDK: **Streamlit** · Space name: e.g. `mawsuat-alrijal` · Public.
3. Upload these files from `Dirayah3/app/` to the Space (web upload or git):
   `rijal_app.py` (rename to **app.py** or set `app_file: rijal_app.py` in README header),
   `db.py`, `ui.py`, `style.css`, `requirements.txt`, `rijal_public.db`.
   Large file note: the web uploader handles big files; with git use `git lfs track "*.db"`.
4. Add `packages.txt` containing one line: `graphviz`  (system package for the network graph).
5. The Space builds automatically → your public link:
   `https://huggingface.co/spaces/<username>/mawsuat-alrijal`

## Option B: Streamlit Community Cloud (needs GitHub + Git LFS for the DB)
1. Push `Dirayah3/app/` to a GitHub repo, with `git lfs track "*.db"` BEFORE adding the DB.
2. https://share.streamlit.io → New app → pick the repo → main file `rijal_app.py`.
3. Public link: `https://<app-name>.streamlit.app`

## Notes
- `db.py` automatically uses `rijal_public.db` when it sits next to the app (deployment),
  and falls back to the full local `rijal_core.db` during development.
- `.streamlit/config.toml` theme: copy the `[theme]` block into the Space's
  `.streamlit/config.toml` (create the folder in the Space) for the parchment colors.
- The app is read-only — safe to share publicly. No API keys are needed at runtime.
