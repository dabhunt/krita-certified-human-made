# Compiled Rust Library Directory

This directory should contain the compiled Rust library (`chm.so`, `chm.pyd`, or `chm.dylib`) built from the parent `certified-human-made` Rust project.

## Building the Library

From the `certified-human-made` directory:

```bash
cargo build --release
```

Then copy the compiled library to this directory:

**Linux**:
```bash
cp target/release/libchm.so krita-plugin/chm_verifier/lib/chm.so
```

**macOS**:
```bash
cp target/release/libchm.dylib krita-plugin/chm_verifier/lib/chm.so
```

**Windows**:
```bash
copy target\release\chm.pyd krita-plugin\chm_verifier\lib\chm.pyd
```

## Note

The linking issues on macOS are expected during development and will be resolved in Phase 3 packaging using `maturin` or manual linker configuration.

