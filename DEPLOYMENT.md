# Drawing-genealogy Deployment Guide

## Quick Deploy to Streamlit Cloud

### Prerequisites

- GitHub repository with your code
- Streamlit Cloud account ([share.streamlit.io](https://share.streamlit.io))

### Required Files

Ensure these files are in your repository:

```
Drawing-genealogy/
├── app.py                    # Main application
├── requirements.txt          # Python dependencies
├── packages.txt             # System packages (APT)
├── utils/
│   ├── formatters.py
│   └── graph_builder.py
└── README.md
```

### Configuration Files

#### 1. requirements.txt
```txt
streamlit
pandas
graphviz
pyvis
openpyxl
```

#### 2. packages.txt
```txt
graphviz
fonts-noto-cjk
```

**Critical:** `fonts-noto-cjk` is required for Japanese character support in PDF output!

### Deployment Steps

1. **Push to GitHub:**
   ```bash
   cd Drawing-genealogy
   git add .
   git commit -m "Deploy Drawing-genealogy with Japanese font support"
   git push origin main
   ```

2. **Deploy on Streamlit Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Select your repository
   - Set **Main file path**: `Drawing-genealogy/app.py`
   - Click "Deploy"

3. **Monitor Deployment:**
   Watch the logs for:
   ```
   Installing system dependencies from packages.txt
   ...
   fonts-noto-cjk is already the newest version
   ```

4. **Verify:**
   - App loads successfully
   - Sidebar shows: OS: `Linux`, フォント: `Noto Sans CJK JP`
   - Upload test Excel file
   - Download PDF - Japanese characters should display

### Troubleshooting Deployment

#### Issue: Deployment fails

**Check:**
1. All files are pushed to GitHub
2. `requirements.txt` has correct package names
3. `packages.txt` uses Unix line endings (LF)
4. No syntax errors in `app.py`

**View logs:**
- Click "Manage app" → "Logs" on Streamlit Cloud

#### Issue: Japanese fonts still not working

**Solution:**
1. Check `packages.txt` contains `fonts-noto-cjk`
2. Reboot the app (forces package reinstall)
3. Check sidebar system info shows correct font

### Testing Before Deploy

Test locally first:

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
streamlit run app.py
```

Open browser to `http://localhost:8501` and verify:
- App loads
- Can upload Excel file
- Graph displays
- PDF downloads
- Japanese characters visible

### Environment Variables (if needed)

If you need to set environment variables:

1. Go to app settings on Streamlit Cloud
2. Add secrets in `.streamlit/secrets.toml` format
3. Access via `st.secrets` in code

### Performance Optimization

For faster deployments:

1. **Cache data:**
   ```python
   @st.cache_data(ttl=600)
   def load_data(file_object):
       # ... your code
   ```

2. **Cache resources:**
   ```python
   @st.cache_resource
   def create_graph():
       # ... your code
   ```

### Updating Deployed App

After making changes:

```bash
git add .
git commit -m "Update: description of changes"
git push
```

Streamlit Cloud auto-deploys within 1-2 minutes.

### Monitoring

Check app health:
- Analytics dashboard on Streamlit Cloud
- View logs for errors
- Monitor resource usage

### Limits (Streamlit Cloud Free Tier)

- **Resources**: 1 CPU, 800 MB RAM
- **Storage**: Limited temporary storage
- **Uptime**: App sleeps after inactivity
- **Bandwidth**: Fair use policy

### Best Practices

1. **Keep dependencies minimal** - only what you need
2. **Use caching** - improve performance and reduce recomputation
3. **Handle errors gracefully** - show user-friendly messages
4. **Test locally first** - verify before deploying
5. **Document requirements** - clear README for users

### Support

If issues persist:
- [Streamlit Community Forum](https://discuss.streamlit.io/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- GitHub issues in your repository
