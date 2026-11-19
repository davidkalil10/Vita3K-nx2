#!/usr/bin/env python3
"""Apply idempotent Nintendo Switch 2 adjustments on top of Switch 1 submodule patches."""
from pathlib import Path
import sys


def replace_once(path: Path, old: str, new: str, marker: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        print(f"Already patched ({marker}): {path}")
        return
    if old not in text:
        raise RuntimeError(f"Expected snippet not found in {path}:\n{old[:200]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
    print(f"Patched ({marker}): {path}")


def patch_oaknut(root: Path) -> None:
    p = root / "external" / "dynarmic" / "externals" / "oaknut" / "include" / "oaknut" / "code_block.hpp"
    if not p.exists():
        raise RuntimeError(f"Missing oaknut code_block.hpp at {p}")

    replace_once(
        p,
        "#    include <switch.h>\n",
        "#    include <switch.h>\n#    ifdef __SWITCH2__\n#        include <kaihen.h>\n#    endif\n",
        "#include <kaihen.h>",
    )

    replace_once(
        p,
        "inline constexpr std::size_t kCodeRegionSize = 128u * 1024u * 1024u;",
        "#if defined(__SWITCH2__)\n"
        "inline constexpr std::size_t kCodeRegionSize = 64u * 1024u * 1024u;\n"
        "#else\n"
        "inline constexpr std::size_t kCodeRegionSize = 128u * 1024u * 1024u;\n"
        "#endif",
        "kCodeRegionSize = 64u * 1024u * 1024u",
    )

    replace_once(
        p,
        "    if (r->jit.type != JitType_CodeMemory) {\n",
        "#if defined(__SWITCH2__)\n"
        "    const bool valid_jit_type = (r->jit.type == JitType_CodeMemory)\n"
        "        || (r->jit.type == JitType_SetProcessMemoryPermission && r->jit.rw_addr != r->jit.src_addr);\n"
        "    if (!valid_jit_type) {\n"
        "#else\n"
        "    if (r->jit.type != JitType_CodeMemory) {\n"
        "#endif\n",
        "valid_jit_type",
    )

    replace_once(
        p,
        "inline bool code_pool_alloc(std::size_t size, std::uint8_t** out_rw, std::uint8_t** out_rx) {",
        "inline bool code_pool_alloc(std::size_t size, std::uint8_t** out_rw, std::uint8_t** out_rx, CodeRegion** out_region = nullptr) {",
        "CodeRegion** out_region = nullptr",
    )

    replace_once(
        p,
        "                *out_rw = r.rw + off;\n"
        "                *out_rx = r.rx + off;\n",
        "                *out_rw = r.rw + off;\n"
        "                *out_rx = r.rx + off;\n"
        "                if (out_region) *out_region = &r;\n",
        "if (out_region) *out_region = &r;",
    )

    replace_once(
        p,
        "            if (switch_detail::code_pool_alloc(size, &rw, &rx)) {",
        "            if (switch_detail::code_pool_alloc(size, &rw, &rx, &m_region)) {",
        "code_pool_alloc(size, &rw, &rx, &m_region)",
    )

    replace_once(
        p,
        "            armDCacheFlush(reinterpret_cast<void*>(rw_base + off), size);\n"
        "            armICacheInvalidate(reinterpret_cast<void*>(rx_base + off), size);\n",
        "#if defined(__SWITCH2__)\n"
        "            if (m_region && m_region->open && m_region->jit.type == JitType_SetProcessMemoryPermission\n"
        "                && m_region->jit.rw_addr != m_region->jit.src_addr) {\n"
        "                const std::size_t region_off = static_cast<std::size_t>(\n"
        "                    (rw_base + off) - reinterpret_cast<std::uintptr_t>(m_region->rw));\n"
        "                const KaihenJitRange range{ static_cast<u64>(region_off), static_cast<u64>(size) };\n"
        "                (void)kaihenJitPublishRanges(&m_region->jit, &range, 1);\n"
        "            } else {\n"
        "                armDCacheFlush(reinterpret_cast<void*>(rw_base + off), size);\n"
        "                armICacheInvalidate(reinterpret_cast<void*>(rx_base + off), size);\n"
        "            }\n"
        "#else\n"
        "            armDCacheFlush(reinterpret_cast<void*>(rw_base + off), size);\n"
        "            armICacheInvalidate(reinterpret_cast<void*>(rx_base + off), size);\n"
        "#endif\n",
        "kaihenJitPublishRanges",
    )

    replace_once(
        p,
        "    std::uint32_t* m_rx_memory = nullptr;\n",
        "    std::uint32_t* m_rx_memory = nullptr;\n    switch_detail::CodeRegion* m_region = nullptr;\n",
        "switch_detail::CodeRegion* m_region",
    )


def patch_ffmpeg_cmake(root: Path) -> None:
    p = root / "external" / "ffmpeg" / "CMakeLists.txt"
    if not p.exists():
        raise RuntimeError(f"Missing external/ffmpeg/CMakeLists.txt at {p}")

    replace_once(
        p,
        "if(SWITCH)\n",
        "if(SWITCH AND NINTENDO_SWITCH2 AND SWITCH2_FFMPEG_DIR)\n"
        "\ttarget_include_directories(${FFMPEG_CORE_NAME} SYSTEM BEFORE INTERFACE \"${SWITCH2_FFMPEG_DIR}/include\")\n"
        "\ttarget_link_libraries(${FFMPEG_CORE_NAME} INTERFACE\n"
        "\t\t\"${SWITCH2_FFMPEG_DIR}/lib/libavformat.a\"\n"
        "\t\t\"${SWITCH2_FFMPEG_DIR}/lib/libavcodec.a\"\n"
        "\t\t\"${SWITCH2_FFMPEG_DIR}/lib/libavfilter.a\"\n"
        "\t\t\"${SWITCH2_FFMPEG_DIR}/lib/libswscale.a\"\n"
        "\t\t\"${SWITCH2_FFMPEG_DIR}/lib/libswresample.a\"\n"
        "\t\t\"${SWITCH2_FFMPEG_DIR}/lib/libavutil.a\"\n"
        "\t\t\"${SWITCH_PORTLIBS}/lib/libdav1d.a\"\n"
        "\t\t\"${SWITCH_PORTLIBS}/lib/libbz2.a\"\n"
        "\t\t\"${SWITCH_PORTLIBS}/lib/libz.a\")\n"
        "\treturn()\n"
        "endif()\n\n"
        "if(SWITCH)\n",
        "if(SWITCH AND NINTENDO_SWITCH2 AND SWITCH2_FFMPEG_DIR)",
    )


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    patch_oaknut(root)
    patch_ffmpeg_cmake(root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
