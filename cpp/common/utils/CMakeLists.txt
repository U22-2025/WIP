target_sources(wipcommon
    PRIVATE
        Auth.cpp
        Cache.cpp
        ConfigLoader.cpp
        FileCache.cpp
    PUBLIC
        Auth.hpp
        Cache.hpp
        ConfigLoader.hpp
        FileCache.hpp
        Utils.hpp
        third_party/json.hpp
)

