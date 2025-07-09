# サブディレクトリなので最低限でOK

# wipcommon に utils のソースを追加
target_sources(wipcommon PRIVATE
    Auth.cpp
    Cache.cpp
    ConfigLoader.cpp
    FileCache.cpp
)

# 必要ならヘッダーファイルも含むディレクトリを追加
target_include_directories(wipcommon PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
