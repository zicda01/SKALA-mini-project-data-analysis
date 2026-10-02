from pathlib import Path

import kagglehub


DATASET = "itshpark/data-driven-prediction-of-battery-cycle"

DATA_DIR = Path("data/raw")

FILES = [
    "2017-05-12_batchdata_updated_struct_errorcorrect.mat",
    "2018-02-20_batchdata_updated_struct_errorcorrect.mat",
    "2018-04-12_batchdata_updated_struct_errorcorrect.mat",
]


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for filename in FILES:
        target = DATA_DIR / filename

        if target.exists():
            print(f"[SKIP] 이미 존재함: {filename}")
            continue

        print(f"[DOWNLOAD] {filename}")

        kagglehub.dataset_download(
            DATASET,
            path=filename,
            output_dir=str(DATA_DIR),
        )

        print(f"[DONE] {filename}")

    print("\n모든 데이터 다운로드 완료")


if __name__ == "__main__":
    main()