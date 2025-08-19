#pragma once

#include "wiplib/client/simple_report_client.hpp"

namespace wiplib::client {

/**
 * @brief SimpleReportClient への互換エイリアス
 *
 * 旧 `ReportClient` の複雑な機能を廃止し、Python 版と同等の
 * シンプルな API に統一しました。
 */
using ReportClient = SimpleReportClient;

} // namespace wiplib::client

