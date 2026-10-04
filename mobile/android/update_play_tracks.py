import urllib.request
import urllib.error
import json
import sys
from google.oauth2 import service_account
from google.auth.transport.requests import Request

PACKAGE_NAME = "com.genaiapps.jevaiflow"
KEY_FILE = r"mobile/android/google-play.json"
SCOPES = ["https://www.googleapis.com/auth/androidpublisher"]

def get_auth_token():
    creds = service_account.Credentials.from_service_account_file(
        KEY_FILE,
        scopes=SCOPES
    )
    creds.refresh(Request())
    return creds.token

def make_request(url, method="GET", data=None, token=None):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"HTTPError {e.code} on {method} {url}:\n{err_msg}", file=sys.stderr)
        raise

def update_tracks():
    token = get_auth_token()
    print("[OK] OAuth2 access token acquired.")

    # 1. Create a new edit
    edit_resp = make_request(
        f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{PACKAGE_NAME}/edits",
        method="POST",
        data={},
        token=token
    )
    edit_id = edit_resp["id"]
    print(f"[OK] Edit created: {edit_id}")

    # 2. List bundles to verify versionCode 3 is present
    bundles = make_request(
        f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{PACKAGE_NAME}/edits/{edit_id}/bundles",
        token=token
    )
    version_codes = [b["versionCode"] for b in bundles.get("bundles", [])]
    print(f"[OK] Existing bundles in edit: {version_codes}")

    release_notes = [
        {
            "language": "en-US",
            "text": "Jev AI Corporate Actions v1.0.2: Redesigned touch UI matching Priority Queue with Urgency badges, 4-Stage Flow Architecture, and Gemini Client Notice election drafting."
        },
        {
            "language": "en-GB",
            "text": "Jev AI Corporate Actions v1.0.2: Redesigned touch UI matching Priority Queue with Urgency badges, 4-Stage Flow Architecture, and Gemini Client Notice election drafting."
        }
    ]

    # 3. Update 'internal' track with version code 3
    internal_track_data = {
        "track": "internal",
        "releases": [
            {
                "name": "1.0.2",
                "versionCodes": ["3"],
                "status": "completed",
                "releaseNotes": release_notes
            }
        ]
    }
    print("Updating 'internal' track with version code 3...")
    internal_resp = make_request(
        f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{PACKAGE_NAME}/edits/{edit_id}/tracks/internal",
        method="PUT",
        data=internal_track_data,
        token=token
    )
    print(f"[OK] 'internal' track updated successfully: {internal_resp.get('track')}")

    # 4. Update 'alpha' (Closed Testing) track with version code 3
    # Try status 'completed', or fallback to 'draft' if draft app restriction applies
    alpha_status = "completed"
    alpha_track_data = {
        "track": "alpha",
        "releases": [
            {
                "name": "1.0.2 (Closed Testing Alpha)",
                "versionCodes": ["3"],
                "status": alpha_status,
                "releaseNotes": release_notes
            }
        ]
    }
    print(f"Updating 'alpha' (Closed Testing) track with status '{alpha_status}'...")
    try:
        alpha_resp = make_request(
            f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{PACKAGE_NAME}/edits/{edit_id}/tracks/alpha",
            method="PUT",
            data=alpha_track_data,
            token=token
        )
        print(f"[OK] 'alpha' track updated successfully: {alpha_resp.get('track')} (status: {alpha_status})")
    except urllib.error.HTTPError as e:
        print("Retrying 'alpha' track with status 'draft'...")
        alpha_track_data["releases"][0]["status"] = "draft"
        alpha_resp = make_request(
            f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{PACKAGE_NAME}/edits/{edit_id}/tracks/alpha",
            method="PUT",
            data=alpha_track_data,
            token=token
        )
        print(f"[OK] 'alpha' track updated successfully with status 'draft': {alpha_resp.get('track')}")

    # 5. Commit the edit to Google Play Console
    print("Committing edit to Google Play Console...")
    commit_resp = make_request(
        f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{PACKAGE_NAME}/edits/{edit_id}:commit",
        method="POST",
        data={},
        token=token
    )
    print(f"[OK] Edit committed successfully! Edit ID: {commit_resp.get('id')}")

    # 6. Verify tracks after commit
    token = get_auth_token()
    new_edit = make_request(
        f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{PACKAGE_NAME}/edits",
        method="POST",
        data={},
        token=token
    )
    verified_tracks = make_request(
        f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{PACKAGE_NAME}/edits/{new_edit['id']}/tracks",
        token=token
    )
    print("\nVerified Current Tracks on Google Play Console:")
    for trk in verified_tracks.get("tracks", []):
        if trk.get("releases"):
            print(f"- Track '{trk['track']}': {json.dumps(trk['releases'], indent=2)}")

if __name__ == "__main__":
    update_tracks()
