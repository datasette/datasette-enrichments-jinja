import asyncio
from datasette.app import Datasette
import pytest
import sqlite_utils


async def _cookies(datasette):
    cookies = {"ds_actor": datasette.sign({"a": {"id": "root"}}, "actor")}
    csrftoken = (
        await datasette.client.get(
            "/-/enrich/data/items/jinja-sandbox", cookies=cookies
        )
    ).cookies["ds_csrftoken"]
    cookies["ds_csrftoken"] = csrftoken
    return cookies


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
    db["items"].insert_all(rows, pk="id")

    cookies = await _cookies(datasette)
    post = {
        "template": "{{ row['name'] }}: {{ row['description'] }}",
        "output_column": "template_output",
    }
    post["csrftoken"] = cookies["ds_csrftoken"]
    response = await datasette.client.post(
        "/-/enrich/data/items/jinja-sandbox",
        data=post,
        cookies=cookies,
    )
    assert response.status_code == 302
    await asyncio.sleep(0.3)
    db = datasette.get_database("data")
    jobs = await db.execute("select * from _enrichment_jobs")
    job = dict(jobs.first())
    assert job["status"] == "finished"
    assert job["enrichment"] == "jinja-sandbox"
    assert job["done_count"] == 3
    results = await db.execute("select * from items order by id")
    rows = [dict(r) for r in results.rows]
    assert rows == [
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
