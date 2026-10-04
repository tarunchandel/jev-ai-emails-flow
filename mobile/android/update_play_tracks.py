import urllib.request
import urllib.error
import json
import os
import sys
from google.oauth2 import service_account
from google.auth.transport.requests import Request

PACKAGE_NAME = "com.genaiapps.jevaiflow"
KEY_FILE = r"mobile/android/google-play.json"
AAB_FILE = r"releases/jev-ai-flow-v1.0.4-release.aab"
TARGET_VERSION_CODE = 5
TARGET_VERSION_NAME = "1.0.4"
SCOPES = ["https://www.googleapis.com/auth/androidpublisher"]

def get_auth_token():
    creds = service_account.Credentials.from_service_account_file(
        KEY_FILE,
        scopes=SCOPES
    )
    creds.refresh(Request())
    return creds.token

def make_request(url, method="GET", data=None, token=None, content_type="application/json"):
    headers = {
        "Authorization": f"Bearer {token}",
    }
    if content_type:
        headers["Content-Type"] = content_type

    if isinstance(data, (dict, list)):
        body = json.dumps(data).encode("utf-8")
    elif isinstance(data, bytes):
        body = data
        headers["Content-Length"] = str(len(data))
    else:
        body = None

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"HTTPError {e.code} on {method} {url}:\n{err_msg}", file=sys.stderr)
        raise

def deploy_to_play_store():
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

    # 2. Check existing bundles in edit
    bundles = make_request(
        f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{PACKAGE_NAME}/edits/{edit_id}/bundles",
        token=token
    )
    version_codes = [b["versionCode"] for b in bundles.get("bundles", [])]
    print(f"[OK] Existing bundles in edit: {version_codes}")

    # 3. Upload AAB if target version code is not in this edit
    if TARGET_VERSION_CODE not in version_codes:
        print(f"Uploading {AAB_FILE} (versionCode: {TARGET_VERSION_CODE})...")
        if not os.path.exists(AAB_FILE):
            raise FileNotFoundError(f"Bundle not found: {AAB_FILE}")
        with open(AAB_FILE, "rb") as f:
            aab_bytes = f.read()

        upload_url = f"https://androidpublisher.googleapis.com/upload/androidpublisher/v3/applications/{PACKAGE_NAME}/edits/{edit_id}/bundles?uploadType=media"
        upload_resp = make_request(
            upload_url,
            method="POST",
            data=aab_bytes,
            token=token,
            content_type="application/octet-stream"
        )
        print(f"[OK] Bundle uploaded successfully! VersionCode: {upload_resp.get('versionCode')} (SHA256: {upload_resp.get('sha256')})")
    else:
        print(f"[OK] Bundle with versionCode {TARGET_VERSION_CODE} already present in edit.")

    release_notes = [
        {
            "language": "en-US",
            "text": f"Jev AI Corporate Actions v{TARGET_VERSION_NAME}: Fixed app launcher icon and adaptive icons across all Android devices, updated splash screen branding, and refreshed web assets."
        },
        {
            "language": "en-GB",
            "text": f"Jev AI Corporate Actions v{TARGET_VERSION_NAME}: Fixed app launcher icon and adaptive icons across all Android devices, updated splash screen branding, and refreshed web assets."
        }
    ]

    # 4. Update 'internal' track with version code
    internal_track_data = {
        "track": "internal",
        "releases": [
            {
                "name": TARGET_VERSION_NAME,
                "versionCodes": [str(TARGET_VERSION_CODE)],
                "status": "completed",
                "releaseNotes": release_notes
            }
        ]
    }
    print(f"Updating 'internal' track with versionCode {TARGET_VERSION_CODE}...")
    internal_resp = make_request(
        f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{PACKAGE_NAME}/edits/{edit_id}/tracks/internal",
        method="PUT",
        data=internal_track_data,
        token=token
    )
    print(f"[OK] 'internal' track updated successfully: {internal_resp.get('track')}")

    # 5. Update 'alpha' (Closed Testing) track with version code
    alpha_status = "completed"
    alpha_track_data = {
        "track": "alpha",
        "releases": [
            {
                "name": f"{TARGET_VERSION_NAME} (Closed Testing)",
                "versionCodes": [str(TARGET_VERSION_CODE)],
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

    # 6. Commit the edit to Google Play Console
    print("Committing edit to Google Play Console...")
    commit_resp = make_request(
        f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{PACKAGE_NAME}/edits/{edit_id}:commit",
        method="POST",
        data={},
        token=token
    )
    print(f"[OK] Edit committed successfully! Edit ID: {commit_resp.get('id')}")

    # 7. Verify tracks after commit
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
    deploy_to_play_store()
