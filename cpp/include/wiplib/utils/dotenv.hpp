#pragma once

#include <string>

namespace wiplib::utils {

// Load environment variables from a .env-style file.
// - path: default ".env"; if relative and not found, search parent dirs.
// - overwrite: if false, don't override already-set variables.
// - max_parent_levels: how many parent directories to search when path is relative.
// Returns true if a file was found and parsed (even if zero keys set).
bool load_dotenv(const std::string& path = ".env", bool overwrite = false, int max_parent_levels = 3);

}

