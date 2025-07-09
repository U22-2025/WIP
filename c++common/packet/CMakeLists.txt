# ライブラリへのソース登録
target_sources(wipcommon
    PRIVATE
        DynamicFormat.cpp
    PUBLIC
        DynamicFormat.hpp
        Packet.hpp
)

add_subdirectory(core)
add_subdirectory(debug)
add_subdirectory(examples)
add_subdirectory(models)
add_subdirectory(types)

