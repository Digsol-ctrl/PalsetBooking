# Rides Module (Django)

This is a self-contained Django app for rides/booking designed to integrate with an existing website hosted on cPanel.

Features:
- Ride booking form with Google Places support
- Pricing engine implementing Zimbabwe USD pricing rules
- Paynow Zimbabwe skeleton integration
- Transactional emails (owner + customer)
- Admin interface for bookings and payments

Quick start (development):
1. Create a virtualenv and install dependencies: `pip install -r requirements.txt`
2. Set environment variables (see `.env.example`)
3. Run migrations: `python manage.py migrate`
4. Create a superuser: `python manage.py createsuperuser`
5. Run the dev server: `python manage.py runserver`

Deployment notes for cPanel:
- Use the Python app feature on cPanel to create a virtualenv and point to `manage.py` as the WSGI entrypoint.
- Create a MySQL database via cPanel and set `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`.
- Configure environment variables in the cPanel app settings or via a `.env` file (ensure it's outside the webroot).
- Set `ALLOWED_HOSTS` to your subdomain or proxy domain.
- Configure SMTP settings (EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD) for transactional emails.
- Ensure `GOOGLE_MAPS_API_KEY` and `PAYNOW_*` settings are set.

Branding colors (from user): **()** — add CSS replacements where necessary in templates.

Contact details (reference):
- Website: https://www.easytransit.co.zw/index.html
- Phone: +263 789 423 154
- Email: enquiries@easytransit.co.zw

Notes:
- The `DistanceService` is a placeholder and must be implemented using the Google Distance Matrix API in production.
- The `PaynowService` is a skeleton — verify fields and signature requirements against Paynow documentation.
- Pricing rules and kid fee calculations are implemented as documented; adjust with business as needed.

Google Maps / Places setup
-------------------------


The booking form uses the Google Maps JavaScript API and the Places (New) Autocomplete component. Before using the booking UI in development or production, ensure the following in your Google Cloud project:

- Enable the **Maps JavaScript API** and **Places API (New)** in the Google Cloud Console (APIs & Services → Library).
- If you perform server-side distance calculations, enable the **Distance Matrix API** or the **Routes API** depending on which service you use.
- Ensure **Billing is enabled** for the project — Maps APIs require billing to be active even for small usage tiers.
- For development, add HTTP referrer restrictions for `http://localhost:8000/*` and `http://127.0.0.1:8000/*` to your API key; for production, restrict to your production domain(s).
- Store your actual API key in a local `.env` (not `.env.example`) or as an environment variable named `GOOGLE_MAPS_API_KEY` and do not commit it to source control.

Example (local `.env`):

```
GOOGLE_MAPS_API_KEY=your_real_key_here
```

If you see console warnings about legacy APIs or `ApiNotActivatedMapError`, confirm you have enabled the correct (new) Places API and that the key's project has billing enabled. The template uses `PlaceAutocompleteElement` and will display a friendly message if the key does not have access to the new Places API.
