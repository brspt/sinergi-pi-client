import requests

CLOUD_RUN_URL = "https://sinergi-model-api-139741896411.asia-southeast2.run.app"

_ENDPOINT = {
    ("hasil_panen", "padi"):    "/v1/panicle/infer",
    ("deteksi_hpt", "padi"):    "/v1/hpt-padi/infer",
    ("hasil_panen", "edamame"): "/v1/edamame/infer",
    ("deteksi_hpt", "edamame"): "/v1/edamame-hpt/infer",
}


def send_to_cloud(
    mode: str,
    plant: str,
    image_bytes: bytes,
    session_id: str,
    sample_slot: int,
) -> dict:
    endpoint = _ENDPOINT.get((mode, plant))
    if not endpoint:
        raise ValueError(f"Mode/tanaman tidak dikenal: {mode}/{plant}")
    resp = requests.post(
        CLOUD_RUN_URL + endpoint,
        files={"file": ("capture.jpg", image_bytes, "image/jpeg")},
        data={"session_id": session_id, "sample_slot": str(sample_slot)},
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json()
