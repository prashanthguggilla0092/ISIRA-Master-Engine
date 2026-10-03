import uuid

from google.cloud import storage

BUCKET_NAME = "prashanth-genai-bucket"
IMAGE_PREFIX = "isira-images"

storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)


def save_image(
    image_bytes: bytes,
    mime_type: str,
    original_filename: str | None = None,
) -> str:
    extension = "jpg"
    if mime_type == "image/png":
        extension = "png"
    elif mime_type == "image/webp":
        extension = "webp"

    filename = original_filename or f"{uuid.uuid4()}.{extension}"
    object_name = f"{IMAGE_PREFIX}/{uuid.uuid4()}-{filename}"

    blob = bucket.blob(object_name)
    blob.upload_from_string(
        image_bytes,
        content_type=mime_type,
    )

    return f"gs://{BUCKET_NAME}/{object_name}"
