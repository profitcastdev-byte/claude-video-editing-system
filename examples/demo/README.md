# Demo project

There is no committed client footage. The demo project is generated:

```bash
python tools/make_demo.py ~/CVES-demo          # add --small for a shorter one
cves --project ~/CVES-demo build               # render + mix + encode
cves --project ~/CVES-demo deliver             # see what a delivery folder looks like
```

The generator draws a presenter (no real person), synthesises a voice and a music bed, and writes everything ingest would have produced: plates, mattes, faces, words, edl and selects. The edit itself is [`tools/demo_edit.yaml`](../../tools/demo_edit.yaml), a lower third, a checklist cutaway, a stat count-up, a roto word and an end card in the neutral default style. It is also a compact worked example of `edit.yaml`.

The golden frames in [`tests/golden/`](../../tests/golden) are this demo rendered by the current engine.
