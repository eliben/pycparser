Basic benchmarking of parsing speed with pycparser.

The ``inputs`` directory contains preprocessed files taken from open source
projects.

Run all inputs from the repository root with:

.. code-block:: sh

   python3 utils/benchmark/benchmark-parse.py utils/benchmark/inputs

``redis.c.pp`` taken from Redis. Generated with:

.. sourcecode::

   gcc -nostdinc -D'__attribute__(x)=' -E -Isrc/ -Ideps/hiredis -Ideps/linenoise -I$HOME/eli/pycparser/utils/fake_libc_include src/redis-cli.c

``tccgen.c.pp`` taken from TCC. Generated with:

.. sourcecode::

   gcc -nostdinc -D'__attribute__(x)=' -E -I.  -I$HOME/eli/pycparser/utils/fake_libc_include tccgen.c

``sqlite-btree.c.pp`` taken from SQLite. Generated with:

.. sourcecode::

   gcc -nostdinc -D'__attribute__(x)=' -E -I. -Isrc/ -I$HOME/eli/pycparser/utils/fake_libc_include src/btree.c

Linux UAPI headers
------------------

The source below includes six Linux UAPI headers covering BPF, Ethernet,
network links, io_uring, netlink, and wireless networking. Their declarations,
enums, and inline functions expand into ``inputs/linux-uapi.c.ppout``. This
input is about 175 KiB and 8,800 lines, uses the default parser dialect, and
needs no kernel checkout to benchmark.

The input was generated from Linux commit
``a804c5742bff224d4cb4d25dd383554d598be32b`` with GCC 13.3 on x86-64.
To regenerate it, run the following from the pycparser repository root. This
requires Git, GCC, Make, and rsync. Exporting UAPI headers does not require a
kernel configuration or a full kernel build.

.. code-block:: sh

   kernel_bench_dir=$(mktemp -d)
   git init "$kernel_bench_dir/linux"
   git -C "$kernel_bench_dir/linux" fetch --depth=1 \
       https://github.com/torvalds/linux.git \
       a804c5742bff224d4cb4d25dd383554d598be32b
   git -C "$kernel_bench_dir/linux" checkout --detach FETCH_HEAD
   make -C "$kernel_bench_dir/linux" O="$kernel_bench_dir/build" \
       ARCH=x86_64 headers_install INSTALL_HDR_PATH="$kernel_bench_dir/headers"

   cat > "$kernel_bench_dir/linux-uapi.c" <<'EOF'
   /* Linux UAPI benchmark input. */
   #include <linux/bpf.h>
   #include <linux/ethtool.h>
   #include <linux/if_link.h>
   #include <linux/io_uring.h>
   #include <linux/netlink.h>
   #include <linux/nl80211.h>
   EOF

   (
       cd "$kernel_bench_dir"
       gcc -E -std=gnu11 -m64 -nostdinc -Iheaders/include \
           '-D__signed__=signed' '-D__extension__=' \
           '-D__inline__=inline' '-D__attribute__(x)=' \
           linux-uapi.c
   ) > utils/benchmark/inputs/linux-uapi.c.ppout

Only exported kernel headers are used; no system or fake libc headers are
needed. The overrides normalize GNU spellings and remove GNU attributes.
Removing attributes loses information such as alignment, so this is a parser
benchmark, not a faithful representation of the kernel ABI. Relative include
paths keep temporary directory names out of the checked-in input while
preserving line directives and header filenames.
