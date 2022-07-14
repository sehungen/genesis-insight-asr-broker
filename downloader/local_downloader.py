import os
import shutil

from .base_downloader import BaseDownloader


class LocalDownloader(BaseDownloader):
    def __init__(self, video_storage_dir):
        self._video_storage_dir = video_storage_dir

    def _process_delete(self, target_path):
        file_path = os.path.join(self._video_storage_dir, target_path)
        os.remove(file_path)

    def _process_downloading(self, filepath, download_path) -> str:
        src_path = os.path.join(self._video_storage_dir, filepath)
        shutil.copyfile(src_path, download_path)
        return download_path

    def _process_uploading(self, src_path, target_path):
        target_path = os.path.join(self._video_storage_dir, target_path)
        os.makedirs(os.path.split(target_path)[0], exist_ok=True)
        shutil.copyfile(src_path, target_path)

    def _process_check(self, target_path) -> bool:
        return os.path.exists(target_path)


def main():
    video_storage_dir = os.path.join(os.getcwd(), 'storage/video/data')
    download_dir = os.path.join(os.getcwd(), 'storage/temp')
    ld = LocalDownloader(video_storage_dir)
    ld.download_file('2.mp4', download_dir)


if __name__ == '__main__':
    main()
