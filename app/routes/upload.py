import csv
import io
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models import UploadResponse

router = APIRouter()


@router.post("/upload")
async def upload_csv(file: UploadFile = File(...)) -> UploadResponse:
    """
    Upload and parse a CSV file containing usernames.

    Expected CSV format: single column with header "username"
    or just a list of usernames.

    Args:
        file: CSV file to upload

    Returns:
        List of parsed usernames
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV file")

    try:
        contents = await file.read()
        content_string = contents.decode("utf-8")

        # Parse CSV
        reader = csv.reader(io.StringIO(content_string))
        rows = list(reader)

        if not rows:
            raise HTTPException(status_code=400, detail="CSV file is empty")

        # Try to detect if first row is a header
        users = []
        start_row = 0

        # Check if first row looks like a header
        first_row = rows[0]
        if (
            len(first_row) > 0
            and first_row[0].lower() in ["username", "user", "email", "account"]
        ):
            start_row = 1

        # Extract usernames from first column
        for row in rows[start_row:]:
            if row and row[0].strip():
                users.append(row[0].strip())

        if not users:
            raise HTTPException(status_code=400, detail="No valid usernames found in CSV")

        return UploadResponse(
            user_count=len(users),
            users=users,
            message=f"Successfully parsed {len(users)} users",
        )

    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be valid UTF-8 text")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing CSV: {str(e)}")
