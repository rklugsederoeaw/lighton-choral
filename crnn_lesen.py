"""Liest die Prüfsysteme (daten/gt/systeme.jsonl) mit einem CRNN-Hybrid aus NMP, ohne Padding.

Aufruf aus natural_music_processing: siehe BERICHT_Zwischenstand.md.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

HIER = Path(__file__).resolve().parent
NMP = HIER.parent
quellen = [
    json.loads(z) for z in (HIER / "daten/gt/systeme.jsonl").read_text().splitlines()
]
ids = {z["id"].split("/")[1]: z for z in quellen}
idx = {}
for q in sorted({z["quelle"] for z in quellen}):
    for x in map(
        json.loads, (NMP / "daten" / q / "music/index.jsonl").read_text().splitlines()
    ):
        if f"{q}/{x['id']}" in {z["id"] for z in quellen}:
            bild = Path(x["image"])
            x["image"] = str(bild if bild.is_absolute() else NMP / "daten" / q / bild)
            x["split"] = "test"
            idx[f"{q}/{x['id']}"] = x
reihe = [z["id"] for z in quellen]
assert all(i in idx for i in reihe), [i for i in reihe if i not in idx][:5]
tmp = Path(tempfile.mkdtemp(prefix="crnn_gt_"))
(tmp / "music").mkdir()
(tmp / "music/index.jsonl").write_text(
    "".join(json.dumps(idx[i]) + "\n" for i in reihe)
)
os.environ["DATA"] = str(tmp)
os.environ.setdefault("MODUS", "hybrid")

import torch  # noqa: E402

sys.path.insert(0, os.environ.get("OMR_CLI_SRC", "omr_cli/src"))  # CRNN code of the project, not included
sys.path.insert(0, str(NMP / "skripte"))
import hybrid as H  # noqa: E402
from core.data.datamodule import pad_collate  # noqa: E402
from core.data.dataset import CTCDataset  # noqa: E402
from core.models.crnn import CRNN_OMR  # noqa: E402


@torch.no_grad()
def main(name):
    i2w = {
        int(k): v
        for k, v in json.load(
            (H.CLI / "vocab" / "volpiano3_musici2w.json").open()
        ).items()
    }
    blank = len(i2w)
    voc = torch.load(H.HERE / "modelle" / "decoder_lm.pt", map_location="cpu")["vocab"]
    w2i = {w: i for i, w in enumerate(voc)}
    bos, eos = w2i["<bos>"], w2i["<eos>"]
    H.MODUS = "scratch"
    model = H.Hybrid(CRNN_OMR(blank + 1), None, blank + 1, len(voc))
    model.load_state_dict(
        torch.load(H.HERE / "modelle" / f"{name}.pt", map_location="cpu")
    )
    model.eval()
    ds = CTCDataset(str(tmp), "test", "music", augment=False)
    ds.set_dictionaries({v: k for k, v in i2w.items()}, i2w)
    assert len(ds) == len(reihe), (len(ds), len(reihe))
    aus = HIER / f"daten/gt/crnn_{name}.jsonl"
    with open(aus, "w", encoding="utf-8") as f:
        for k in range(len(ds)):
            X, _, FL, _ = pad_collate([ds[k]])
            h = model.encode(X)
            c = H.ctc_greedy(model.ctc(h).log_softmax(-1)[0], FL[0].item(), blank, i2w)
            a = H.att_greedy(model, h, FL, voc, bos, eos)[0]
            z = quellen[k]
            f.write(
                json.dumps(
                    {
                        "id": z["id"],
                        "quelle": z["quelle"],
                        "label": z["label"],
                        "ctc": " ".join(c) if isinstance(c, list) else c,
                        "att": " ".join(a) if isinstance(a, list) else a,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            if (k + 1) % 50 == 0:
                print(k + 1, flush=True)
    print("fertig", aus)


main(sys.argv[1])
