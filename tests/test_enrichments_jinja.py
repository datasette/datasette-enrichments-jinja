from datasette.app import Datasette
from datasette_enrichments_jinja import JinjaSandbox
import pytest
import sqlite_utils


@pytest.mark.asyncio
async def test_enrichment(tmpdir):
    data = str(tmpdir / "data.db")
    datasette = Datasette([data], memory=True)
    db = sqlite_utils.Database(data)
    rows = [
        {"id": 1, "name": "One", "description": "First item"},
        {"id": 2, "name": "Two", "description": "Second item"},
        {"id": 3, "name": "Three", "description": "Third item"},
    ]
    config = {
        "output_column": ["template_output"],
        "template": ["{{ row['name'] }}: {{ row['description'] }}"],
    }
    db["items"].insert_all(rows)
    ds_db = datasette.get_database("data")
    enrichment = JinjaSandbox()
    await enrichment.initialize(ds_db, "items", config)
    # It should now have a template_output column
    assert "template_output" in db["items"].columns_dict
    # Now enrich the batch
    await enrichment.enrich_batch(
        db=ds_db,
        table="items",
        rows=rows,
        pks=["id"],
        config={
            "output_column": ["template_output"],
            "template": ["{{ row['name'] }}: {{ row['description'] }}"],
        },
        job_id=1,
    )
    new_rows = list(db["items"].rows)
    assert new_rows == [
        {
            "id": 1,
            "name": "One",
            "description": "First item",
            "template_output": "One: First item",
        },
        {
            "id": 2,
            "name": "Two",
            "description": "Second item",
            "template_output": "Two: Second item",
        },
        {
            "id": 3,
            "name": "Three",
            "description": "Third item",
            "template_output": "Three: Third item",
        },
    ]
