#include "wiplib/utils/dotenv.hpp"
#include "wiplib/utils/posix_wrapper.hpp"

#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <fstream>
#include <optional>
#include <sstream>
#include <string>
#include <system_error>

#if __has_include(<filesystem>)
#include <filesystem>
namespace fs = std::filesystem;
#else
#error "C++17 filesystem is required"
#endif

namespace wiplib::utils {

namespace {

static inline std::string trim(std::string s) {
  auto not_space = [](unsigned char ch) { return !std::isspace(ch); };
  s.erase(s.begin(), std::find_if(s.begin(), s.end(), not_space));
  s.erase(std::find_if(s.rbegin(), s.rend(), not_space).base(), s.end());
  return s;
}

static inline bool is_valid_key_char(char c) {
  return std::isalnum(static_cast<unsigned char>(c)) || c == '_';
}

static inline std::string unquote(std::string v) {
  if (v.size() >= 2) {
    if ((v.front() == '"' && v.back() == '"') ||
        (v.front() == '\'' && v.back() == '\'')) {
      v = v.substr(1, v.size() - 2);
    }
  }
  return v;
}

static std::optional<fs::path> resolve_env_path(const std::string &path,
                                                int max_parent_levels) {
  // If absolute, use as-is
  fs::path p(path);
  if (p.is_absolute()) {
    if (fs::exists(p) && fs::is_regular_file(p))
      return p;
    return std::nullopt;
  }

  // Allow override via WIP_DOTENV_PATH
  if (const char *custom = std::getenv("WIP_DOTENV_PATH")) {
    fs::path cp(custom);
    if (fs::exists(cp) && fs::is_regular_file(cp))
      return cp;
  }

  // Search current directory and up to N parents
  fs::path cur = fs::current_path();
  for (int i = 0; i <= max_parent_levels; ++i) {
    fs::path candidate = cur / p;
    if (fs::exists(candidate) && fs::is_regular_file(candidate)) {
      return candidate;
    }
    if (!cur.has_parent_path())
      break;
    cur = cur.parent_path();
  }
  return std::nullopt;
}

} // namespace

bool load_dotenv(const std::string &path, bool overwrite,
                 int max_parent_levels) {
  static bool loaded_once = false;
  // If already loaded and not overwriting, we can return quickly. Still try to
  // find file for return value accuracy.
  auto file_path = resolve_env_path(path, max_parent_levels);
  if (!file_path)
    return false;

  // Avoid re-parsing unless overwrite requested
  if (loaded_once && !overwrite)
    return true;

  std::ifstream ifs(*file_path);
  if (!ifs)
    return false;

  std::string line;
  while (std::getline(ifs, line)) {
    std::string s = trim(line);
    if (s.empty())
      continue;
    if (s[0] == '#')
      continue;

    // Find '=' separator
    auto eq = s.find('=');
    if (eq == std::string::npos)
      continue;
    std::string key = trim(s.substr(0, eq));
    std::string val = trim(s.substr(eq + 1));

    // Validate key characters
    if (key.empty() || !std::all_of(key.begin(), key.end(), is_valid_key_char))
      continue;

    // Handle optional export prefix
    if (key.rfind("export ", 0) == 0) {
      key = trim(key.substr(7));
      if (key.empty() ||
          !std::all_of(key.begin(), key.end(), is_valid_key_char))
        continue;
    }

    // Allow quoted values
    val = unquote(val);

    // Do not override unless allowed
    PosixWrapper::setEnv(key, val, overwrite);
  }

  loaded_once = true;
  return true;
}

} // namespace wiplib::utils
