# `scp` and `rsync`

## Copying a file
### `scp`
Local to server: `scp user@host:/path/to/remote/file.txt /local/directory/`
Server to local: `scp /local/file.txt user@host:/path/to/remote/directory/`

### `rsync`
Local to server: `rsync -<tags-here> user@host:/path/to/remote/file.txt /local/directory/`
Server to local: `rsync -<tags-here> /local/file.txt user@host:/path/to/remote/directory/`

Common tags for `rsync` include a, v, and z.
    * The `z` tag tells `rsync` to compress the file in transit for faster copying.
    * The `v` tag tells `rsync` to run in verbose mode. Without this tag, it will fail without any error message.
    * The `a` tag tells `rsync` to copy the file with the same permissions, based on UID, as the original file.
