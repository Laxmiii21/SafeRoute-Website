# SafeRoute Website (Flask)

This is a separate browser-based version of SafeRoute. It does not overwrite your Tkinter application.

## Run locally on Ubuntu
```bash
cd SafeRoute_Website
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

If virtual-environment creation fails:
```bash
sudo apt update
sudo apt install python3-venv
```

## Create a public link for your presentation
1. Upload the contents of this folder to a GitHub repository.
2. Sign in to Render and create a new Web Service connected to the repository.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Deploy and share the HTTPS URL Render gives you. A public URL is not created until you deploy it through your own hosting account.

## Included
- Responsive website dashboard and safety ticker
- Journey form and Google Maps directions
- Route comparison using a simple explainable indicator
- Browser geolocation and Google Maps location link
- Up to two trusted emergency contacts
- SOS message preparation and phone/SMS shortcuts
- Incident reporting marked UNVERIFIED

## Honest prototype limitations
- Sample routes are illustrative, not real-time verified safety information.
- Browser location depends on permissions/device accuracy; HTTPS is normally required for geolocation on a hosted site.
- SOS opens phone actions for the user to confirm; it does not silently send SMS or automatically call contacts.
- Incident reports are stored in this server's SQLite database and are not a shared, moderated public network.
- This prototype does not control a phone's physical flashlight because browser support is inconsistent.
- SQLite storage on some free hosting services may reset or be temporary. Use a persistent database for a production service.
