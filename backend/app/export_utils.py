import csv
from io import StringIO
from fastapi.responses import StreamingResponse

def export_csv(rows, columns, filename="export.csv"):
    sio = StringIO()
    writer = csv.DictWriter(sio, fieldnames=columns)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    sio.seek(0)
    return StreamingResponse(sio, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})
