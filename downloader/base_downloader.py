import os


class BaseDownloader(object):

    def delete_file(self, target_path):
        self._process_delete(target_path)

    def download_file(self, src_path, target_dir) -> str:
        download_path = self._make_download_path(target_dir, src_path)
        self._process_downloading(src_path, download_path)

        return download_path

    def upload_file(self, src_path, target_path):
        self._process_uploading(src_path, target_path)

    def check_file(self, target_path) -> bool:
        return self._process_check(target_path)

    @staticmethod
    def _make_download_path(download_dir, filepath):
        download_path = os.path.join(download_dir, os.path.basename(filepath))
        return download_path

    def _process_delete(self, target_path):
        pass

    def _process_downloading(self, src_path, download_path):
        pass

    def _process_uploading(self, src_path, upload_path):
        pass

    def _process_check(self, target_path) -> bool:
        pass