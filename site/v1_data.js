/* Knowledge Hub v1 projection client and route/date helpers.
 * ES5-compatible syntax for Safari 12. */
(function (root, factory) {
  "use strict";
  var api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.KnowledgeV1Data = api;
}(typeof window !== "undefined" ? window : (typeof globalThis !== "undefined" ? globalThis : this), function () {
  "use strict";

  var CACHE_NAME = "knowledge-hub-v1-public-data";
  var UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
  var DATE = /^\d{4}-\d{2}-\d{2}$/;
  var MONTH = /^\d{4}-\d{2}$/;
  var actionNames = {CREATED: 1, UPDATED: 1, MOVED: 1, ARCHIVED: 1, REOPENED: 1, IMPORTED: 1};
  var statusNames = {draft: 1, stable: 1, in_progress: 1, completed: 1, deprecated: 1};
  var routeQuery = {
    "/today": [], "/projects": [], "/records": ["q", "area", "project", "type", "status", "tag", "archived", "sort"],
    "/diary": ["date", "mode", "project", "area", "type", "status", "tag", "action"],
    "/calendar": ["month", "day", "project", "archived"]
  };

  function HubError(code, message, status, url) {
    this.name = "KnowledgeV1DataError";
    this.code = code;
    this.message = message || code;
    this.status = status || 0;
    this.url = url || "";
    if (Error.captureStackTrace) Error.captureStackTrace(this, HubError);
  }
  HubError.prototype = Object.create(Error.prototype);
  HubError.prototype.constructor = HubError;

  function validDate(value) {
    if (typeof value !== "string" || !DATE.test(value)) return false;
    var d = new Date(value + "T00:00:00Z");
    return !isNaN(d.getTime()) && d.toISOString().slice(0, 10) === value;
  }
  function utcDate(value) {
    var d;
    if (value instanceof Date) d = new Date(Date.UTC(value.getUTCFullYear(), value.getUTCMonth(), value.getUTCDate()));
    else if (validDate(value)) d = new Date(value + "T00:00:00Z");
    else throw new HubError("invalid_date", "Invalid UTC date");
    return d;
  }
  function dateString(d) { return d.toISOString().slice(0, 10); }
  function mondayStart(value) {
    var d = utcDate(value);
    d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7));
    return dateString(d);
  }
  function shiftDays(value, amount) {
    var d = utcDate(value);
    d.setUTCDate(d.getUTCDate() + amount);
    return dateString(d);
  }
  function shiftMonth(value, amount) {
    var isDate = typeof value === "string" && DATE.test(value);
    var parts = typeof value === "string" && (MONTH.test(value) || isDate) ? value.slice(0, 7).split("-") : null;
    if (!parts) throw new HubError("invalid_month", "Invalid month");
    var year = Number(parts[0]), month = Number(parts[1]) - 1;
    if (month < 0 || month > 11) throw new HubError("invalid_month", "Invalid month");
    var day = 1;
    // Accept YYYY-MM-DD as well so diary month navigation can preserve/clamp its day.
    if (isDate) {
      if (!validDate(value)) throw new HubError("invalid_date", "Invalid date");
      day = Number(value.slice(8, 10));
    }
    var target = new Date(Date.UTC(year, month + amount, 1));
    var last = new Date(Date.UTC(target.getUTCFullYear(), target.getUTCMonth() + 1, 0)).getUTCDate();
    target.setUTCDate(Math.min(day, last));
    return isDate ? dateString(target) : target.toISOString().slice(0, 7);
  }
  function monthBounds(month) {
    if (!MONTH.test(month) || Number(month.slice(5)) < 1 || Number(month.slice(5)) > 12) throw new HubError("invalid_month", "Invalid month");
    var start = month + "-01";
    var d = new Date(start + "T00:00:00Z");
    d.setUTCMonth(d.getUTCMonth() + 1);
    return {start: start, end: shiftDays(dateString(d), -1)};
  }

  function getParam(params, key) { return params.has(key) ? params.get(key) : ""; }
  function parseRoute(hash) {
    var text = typeof hash === "string" ? hash : "";
    if (text.charAt(0) === "#") text = text.slice(1);
    if (!text) text = "/diary";
    var split = text.indexOf("?");
    var path = split < 0 ? text : text.slice(0, split);
    var query = split < 0 ? "" : text.slice(split + 1);
    if (!path || path.charAt(0) !== "/") return {state: "invalid", reason: "route"};
    var parts = path.split("/").slice(1);
    if (parts.length === 2 && parts[0] === "records") {
      if (!UUID.test(parts[1])) return {state: "invalid", reason: "id"};
      var recordParams = new URLSearchParams(query);
      var tab = getParam(recordParams, "tab") || "content";
      if (["content", "history", "source"].indexOf(tab) < 0 || Array.from(recordParams.keys()).some(function (k) { return k !== "tab"; })) return {state: "invalid", reason: "query"};
      return {route: "record", id: parts[1], tab: tab};
    }
    if (parts.length === 2 && parts[0] === "projects") {
      if (!UUID.test(parts[1])) return {state: "invalid", reason: "id"};
      var projectParams = new URLSearchParams(query), projectResult = {route: "project", id: parts[1]}, projectInvalid = false;
      projectParams.forEach(function (value, name) { if (["status", "tag"].indexOf(name) < 0 || name === "status" && !statusNames[value]) projectInvalid = true; else projectResult[name] = value; });
      return projectInvalid ? {state: "invalid", reason: "query"} : projectResult;
    }
    if (parts.length === 2 && parts[0] === "events") {
      if (!UUID.test(parts[1])) return {state: "invalid", reason: "id"};
      var eventParams = new URLSearchParams(query);
      var view = getParam(eventParams, "view") || "revision";
      if (["revision", "before", "diff"].indexOf(view) < 0 || Array.from(eventParams.keys()).some(function (k) { return k !== "view"; })) return {state: "invalid", reason: "query"};
      return {route: "event", id: parts[1], view: view};
    }
    var key = "/" + parts.join("/");
    if (!Object.prototype.hasOwnProperty.call(routeQuery, key)) return {state: "not_found"};
    var params = new URLSearchParams(query), allowed = routeQuery[key];
    var invalid = false;
    params.forEach(function (_, name) { if (allowed.indexOf(name) < 0) invalid = true; });
    var output = {route: key.slice(1)};
    if (invalid) return {state: "invalid", reason: "query"};
    params.forEach(function (value, name) { output[name] = value; });
    if (key === "/diary") {
      if (output.mode && ["day", "week", "month"].indexOf(output.mode) < 0) invalid = true;
      if (output.date && !validDate(output.date)) invalid = true;
      if (output.action && !actionNames[output.action]) invalid = true;
      if (output.status && !statusNames[output.status]) invalid = true;
    }
    if (key === "/calendar") {
      if (output.month && (!MONTH.test(output.month) || Number(output.month.slice(5)) < 1 || Number(output.month.slice(5)) > 12)) invalid = true;
      if (output.day && !validDate(output.day)) invalid = true;
      if (output.month && output.day && output.month !== output.day.slice(0, 7)) invalid = true;
    }
    if ((key === "/records" || key === "/projects") && output.archived && output.archived !== "1") invalid = true;
    if (key === "/records" && output.sort && ["title", "updated"].indexOf(output.sort) < 0) invalid = true;
    if (key === "/records" && output.status && !statusNames[output.status]) invalid = true;
    if (key === "/projects" && output.status && !statusNames[output.status]) invalid = true;
    if (invalid) return {state: "invalid", reason: "value"};
    return output;
  }
  function serializeRoute(route) {
    if (!route || typeof route !== "object") throw new HubError("invalid_route", "Invalid route");
    var path, params = new URLSearchParams(), known;
    if (route.route === "record") { path = "/records/" + route.id; if (route.tab && route.tab !== "content") params.set("tab", route.tab); }
    else if (route.route === "project") { path = "/projects/" + route.id; if (route.status) params.set("status", route.status); if (route.tag) params.set("tag", route.tag); }
    else if (route.route === "event") { path = "/events/" + route.id; if (route.view && route.view !== "revision") params.set("view", route.view); }
    else {
      path = "/" + route.route;
      known = routeQuery[path];
      if (!known) throw new HubError("invalid_route", "Unknown route");
      var defaults = {date: "", mode: "week", sort: "title", archived: "0"};
      known.forEach(function (key) {
        var value = route[key];
        if (value !== undefined && value !== null && value !== "" && String(value) !== (defaults[key] || "")) params.set(key, String(value));
      });
    }
    var suffix = params.toString();
    return "#" + path + (suffix ? "?" + suffix : "");
  }

  // Generated from Python Unicode 15.0.0 str.isalnum() to match the exporter.
  var ALNUM_RANGES = [
    48, 57, 65, 90, 97, 122, 170, 170, 178, 179, 181, 181,
    185, 186, 188, 190, 192, 214, 216, 246, 248, 705, 710, 721,
    736, 740, 748, 748, 750, 750, 880, 884, 886, 887, 890, 893,
    895, 895, 902, 902, 904, 906, 908, 908, 910, 929, 931, 1013,
    1015, 1153, 1162, 1327, 1329, 1366, 1369, 1369, 1376, 1416, 1488, 1514,
    1519, 1522, 1568, 1610, 1632, 1641, 1646, 1647, 1649, 1747, 1749, 1749,
    1765, 1766, 1774, 1788, 1791, 1791, 1808, 1808, 1810, 1839, 1869, 1957,
    1969, 1969, 1984, 2026, 2036, 2037, 2042, 2042, 2048, 2069, 2074, 2074,
    2084, 2084, 2088, 2088, 2112, 2136, 2144, 2154, 2160, 2183, 2185, 2190,
    2208, 2249, 2308, 2361, 2365, 2365, 2384, 2384, 2392, 2401, 2406, 2415,
    2417, 2432, 2437, 2444, 2447, 2448, 2451, 2472, 2474, 2480, 2482, 2482,
    2486, 2489, 2493, 2493, 2510, 2510, 2524, 2525, 2527, 2529, 2534, 2545,
    2548, 2553, 2556, 2556, 2565, 2570, 2575, 2576, 2579, 2600, 2602, 2608,
    2610, 2611, 2613, 2614, 2616, 2617, 2649, 2652, 2654, 2654, 2662, 2671,
    2674, 2676, 2693, 2701, 2703, 2705, 2707, 2728, 2730, 2736, 2738, 2739,
    2741, 2745, 2749, 2749, 2768, 2768, 2784, 2785, 2790, 2799, 2809, 2809,
    2821, 2828, 2831, 2832, 2835, 2856, 2858, 2864, 2866, 2867, 2869, 2873,
    2877, 2877, 2908, 2909, 2911, 2913, 2918, 2927, 2929, 2935, 2947, 2947,
    2949, 2954, 2958, 2960, 2962, 2965, 2969, 2970, 2972, 2972, 2974, 2975,
    2979, 2980, 2984, 2986, 2990, 3001, 3024, 3024, 3046, 3058, 3077, 3084,
    3086, 3088, 3090, 3112, 3114, 3129, 3133, 3133, 3160, 3162, 3165, 3165,
    3168, 3169, 3174, 3183, 3192, 3198, 3200, 3200, 3205, 3212, 3214, 3216,
    3218, 3240, 3242, 3251, 3253, 3257, 3261, 3261, 3293, 3294, 3296, 3297,
    3302, 3311, 3313, 3314, 3332, 3340, 3342, 3344, 3346, 3386, 3389, 3389,
    3406, 3406, 3412, 3414, 3416, 3425, 3430, 3448, 3450, 3455, 3461, 3478,
    3482, 3505, 3507, 3515, 3517, 3517, 3520, 3526, 3558, 3567, 3585, 3632,
    3634, 3635, 3648, 3654, 3664, 3673, 3713, 3714, 3716, 3716, 3718, 3722,
    3724, 3747, 3749, 3749, 3751, 3760, 3762, 3763, 3773, 3773, 3776, 3780,
    3782, 3782, 3792, 3801, 3804, 3807, 3840, 3840, 3872, 3891, 3904, 3911,
    3913, 3948, 3976, 3980, 4096, 4138, 4159, 4169, 4176, 4181, 4186, 4189,
    4193, 4193, 4197, 4198, 4206, 4208, 4213, 4225, 4238, 4238, 4240, 4249,
    4256, 4293, 4295, 4295, 4301, 4301, 4304, 4346, 4348, 4680, 4682, 4685,
    4688, 4694, 4696, 4696, 4698, 4701, 4704, 4744, 4746, 4749, 4752, 4784,
    4786, 4789, 4792, 4798, 4800, 4800, 4802, 4805, 4808, 4822, 4824, 4880,
    4882, 4885, 4888, 4954, 4969, 4988, 4992, 5007, 5024, 5109, 5112, 5117,
    5121, 5740, 5743, 5759, 5761, 5786, 5792, 5866, 5870, 5880, 5888, 5905,
    5919, 5937, 5952, 5969, 5984, 5996, 5998, 6000, 6016, 6067, 6103, 6103,
    6108, 6108, 6112, 6121, 6128, 6137, 6160, 6169, 6176, 6264, 6272, 6276,
    6279, 6312, 6314, 6314, 6320, 6389, 6400, 6430, 6470, 6509, 6512, 6516,
    6528, 6571, 6576, 6601, 6608, 6618, 6656, 6678, 6688, 6740, 6784, 6793,
    6800, 6809, 6823, 6823, 6917, 6963, 6981, 6988, 6992, 7001, 7043, 7072,
    7086, 7141, 7168, 7203, 7232, 7241, 7245, 7293, 7296, 7304, 7312, 7354,
    7357, 7359, 7401, 7404, 7406, 7411, 7413, 7414, 7418, 7418, 7424, 7615,
    7680, 7957, 7960, 7965, 7968, 8005, 8008, 8013, 8016, 8023, 8025, 8025,
    8027, 8027, 8029, 8029, 8031, 8061, 8064, 8116, 8118, 8124, 8126, 8126,
    8130, 8132, 8134, 8140, 8144, 8147, 8150, 8155, 8160, 8172, 8178, 8180,
    8182, 8188, 8304, 8305, 8308, 8313, 8319, 8329, 8336, 8348, 8450, 8450,
    8455, 8455, 8458, 8467, 8469, 8469, 8473, 8477, 8484, 8484, 8486, 8486,
    8488, 8488, 8490, 8493, 8495, 8505, 8508, 8511, 8517, 8521, 8526, 8526,
    8528, 8585, 9312, 9371, 9450, 9471, 10102, 10131, 11264, 11492, 11499, 11502,
    11506, 11507, 11517, 11517, 11520, 11557, 11559, 11559, 11565, 11565, 11568, 11623,
    11631, 11631, 11648, 11670, 11680, 11686, 11688, 11694, 11696, 11702, 11704, 11710,
    11712, 11718, 11720, 11726, 11728, 11734, 11736, 11742, 11823, 11823, 12293, 12295,
    12321, 12329, 12337, 12341, 12344, 12348, 12353, 12438, 12445, 12447, 12449, 12538,
    12540, 12543, 12549, 12591, 12593, 12686, 12690, 12693, 12704, 12735, 12784, 12799,
    12832, 12841, 12872, 12879, 12881, 12895, 12928, 12937, 12977, 12991, 13312, 19903,
    19968, 42124, 42192, 42237, 42240, 42508, 42512, 42539, 42560, 42606, 42623, 42653,
    42656, 42735, 42775, 42783, 42786, 42888, 42891, 42954, 42960, 42961, 42963, 42963,
    42965, 42969, 42994, 43009, 43011, 43013, 43015, 43018, 43020, 43042, 43056, 43061,
    43072, 43123, 43138, 43187, 43216, 43225, 43250, 43255, 43259, 43259, 43261, 43262,
    43264, 43301, 43312, 43334, 43360, 43388, 43396, 43442, 43471, 43481, 43488, 43492,
    43494, 43518, 43520, 43560, 43584, 43586, 43588, 43595, 43600, 43609, 43616, 43638,
    43642, 43642, 43646, 43695, 43697, 43697, 43701, 43702, 43705, 43709, 43712, 43712,
    43714, 43714, 43739, 43741, 43744, 43754, 43762, 43764, 43777, 43782, 43785, 43790,
    43793, 43798, 43808, 43814, 43816, 43822, 43824, 43866, 43868, 43881, 43888, 44002,
    44016, 44025, 44032, 55203, 55216, 55238, 55243, 55291, 63744, 64109, 64112, 64217,
    64256, 64262, 64275, 64279, 64285, 64285, 64287, 64296, 64298, 64310, 64312, 64316,
    64318, 64318, 64320, 64321, 64323, 64324, 64326, 64433, 64467, 64829, 64848, 64911,
    64914, 64967, 65008, 65019, 65136, 65140, 65142, 65276, 65296, 65305, 65313, 65338,
    65345, 65370, 65382, 65470, 65474, 65479, 65482, 65487, 65490, 65495, 65498, 65500,
    65536, 65547, 65549, 65574, 65576, 65594, 65596, 65597, 65599, 65613, 65616, 65629,
    65664, 65786, 65799, 65843, 65856, 65912, 65930, 65931, 66176, 66204, 66208, 66256,
    66273, 66299, 66304, 66339, 66349, 66378, 66384, 66421, 66432, 66461, 66464, 66499,
    66504, 66511, 66513, 66517, 66560, 66717, 66720, 66729, 66736, 66771, 66776, 66811,
    66816, 66855, 66864, 66915, 66928, 66938, 66940, 66954, 66956, 66962, 66964, 66965,
    66967, 66977, 66979, 66993, 66995, 67001, 67003, 67004, 67072, 67382, 67392, 67413,
    67424, 67431, 67456, 67461, 67463, 67504, 67506, 67514, 67584, 67589, 67592, 67592,
    67594, 67637, 67639, 67640, 67644, 67644, 67647, 67669, 67672, 67702, 67705, 67742,
    67751, 67759, 67808, 67826, 67828, 67829, 67835, 67867, 67872, 67897, 67968, 68023,
    68028, 68047, 68050, 68096, 68112, 68115, 68117, 68119, 68121, 68149, 68160, 68168,
    68192, 68222, 68224, 68255, 68288, 68295, 68297, 68324, 68331, 68335, 68352, 68405,
    68416, 68437, 68440, 68466, 68472, 68497, 68521, 68527, 68608, 68680, 68736, 68786,
    68800, 68850, 68858, 68899, 68912, 68921, 69216, 69246, 69248, 69289, 69296, 69297,
    69376, 69415, 69424, 69445, 69457, 69460, 69488, 69505, 69552, 69579, 69600, 69622,
    69635, 69687, 69714, 69743, 69745, 69746, 69749, 69749, 69763, 69807, 69840, 69864,
    69872, 69881, 69891, 69926, 69942, 69951, 69956, 69956, 69959, 69959, 69968, 70002,
    70006, 70006, 70019, 70066, 70081, 70084, 70096, 70106, 70108, 70108, 70113, 70132,
    70144, 70161, 70163, 70187, 70207, 70208, 70272, 70278, 70280, 70280, 70282, 70285,
    70287, 70301, 70303, 70312, 70320, 70366, 70384, 70393, 70405, 70412, 70415, 70416,
    70419, 70440, 70442, 70448, 70450, 70451, 70453, 70457, 70461, 70461, 70480, 70480,
    70493, 70497, 70656, 70708, 70727, 70730, 70736, 70745, 70751, 70753, 70784, 70831,
    70852, 70853, 70855, 70855, 70864, 70873, 71040, 71086, 71128, 71131, 71168, 71215,
    71236, 71236, 71248, 71257, 71296, 71338, 71352, 71352, 71360, 71369, 71424, 71450,
    71472, 71483, 71488, 71494, 71680, 71723, 71840, 71922, 71935, 71942, 71945, 71945,
    71948, 71955, 71957, 71958, 71960, 71983, 71999, 71999, 72001, 72001, 72016, 72025,
    72096, 72103, 72106, 72144, 72161, 72161, 72163, 72163, 72192, 72192, 72203, 72242,
    72250, 72250, 72272, 72272, 72284, 72329, 72349, 72349, 72368, 72440, 72704, 72712,
    72714, 72750, 72768, 72768, 72784, 72812, 72818, 72847, 72960, 72966, 72968, 72969,
    72971, 73008, 73030, 73030, 73040, 73049, 73056, 73061, 73063, 73064, 73066, 73097,
    73112, 73112, 73120, 73129, 73440, 73458, 73474, 73474, 73476, 73488, 73490, 73523,
    73552, 73561, 73648, 73648, 73664, 73684, 73728, 74649, 74752, 74862, 74880, 75075,
    77712, 77808, 77824, 78895, 78913, 78918, 82944, 83526, 92160, 92728, 92736, 92766,
    92768, 92777, 92784, 92862, 92864, 92873, 92880, 92909, 92928, 92975, 92992, 92995,
    93008, 93017, 93019, 93025, 93027, 93047, 93053, 93071, 93760, 93846, 93952, 94026,
    94032, 94032, 94099, 94111, 94176, 94177, 94179, 94179, 94208, 100343, 100352, 101589,
    101632, 101640, 110576, 110579, 110581, 110587, 110589, 110590, 110592, 110882, 110898, 110898,
    110928, 110930, 110933, 110933, 110948, 110951, 110960, 111355, 113664, 113770, 113776, 113788,
    113792, 113800, 113808, 113817, 119488, 119507, 119520, 119539, 119648, 119672, 119808, 119892,
    119894, 119964, 119966, 119967, 119970, 119970, 119973, 119974, 119977, 119980, 119982, 119993,
    119995, 119995, 119997, 120003, 120005, 120069, 120071, 120074, 120077, 120084, 120086, 120092,
    120094, 120121, 120123, 120126, 120128, 120132, 120134, 120134, 120138, 120144, 120146, 120485,
    120488, 120512, 120514, 120538, 120540, 120570, 120572, 120596, 120598, 120628, 120630, 120654,
    120656, 120686, 120688, 120712, 120714, 120744, 120746, 120770, 120772, 120779, 120782, 120831,
    122624, 122654, 122661, 122666, 122928, 122989, 123136, 123180, 123191, 123197, 123200, 123209,
    123214, 123214, 123536, 123565, 123584, 123627, 123632, 123641, 124112, 124139, 124144, 124153,
    124896, 124902, 124904, 124907, 124909, 124910, 124912, 124926, 124928, 125124, 125127, 125135,
    125184, 125251, 125259, 125259, 125264, 125273, 126065, 126123, 126125, 126127, 126129, 126132,
    126209, 126253, 126255, 126269, 126464, 126467, 126469, 126495, 126497, 126498, 126500, 126500,
    126503, 126503, 126505, 126514, 126516, 126519, 126521, 126521, 126523, 126523, 126530, 126530,
    126535, 126535, 126537, 126537, 126539, 126539, 126541, 126543, 126545, 126546, 126548, 126548,
    126551, 126551, 126553, 126553, 126555, 126555, 126557, 126557, 126559, 126559, 126561, 126562,
    126564, 126564, 126567, 126570, 126572, 126578, 126580, 126583, 126585, 126588, 126590, 126590,
    126592, 126601, 126603, 126619, 126625, 126627, 126629, 126633, 126635, 126651, 127232, 127244,
    130032, 130041, 131072, 173791, 173824, 177977, 177984, 178205, 178208, 183969, 183984, 191456,
    194560, 195101, 196608, 201546, 201552, 205743,
  ];

  function isAlnum(code) {
    var low = 0, high = ALNUM_RANGES.length / 2 - 1, mid, start, end;
    while (low <= high) {
      mid = (low + high) >> 1; start = ALNUM_RANGES[mid * 2]; end = ALNUM_RANGES[mid * 2 + 1];
      if (code < start) high = mid - 1; else if (code > end) low = mid + 1; else return true;
    }
    return false;
  }
  function tokens(query) {
    var normalized = String(query || "").normalize("NFC").toLowerCase();
    var out = [], current = "", cps = Array.from(normalized), i, cp;
    for (i = 0; i < cps.length; i += 1) {
      cp = cps[i].codePointAt(0);
      if (isAlnum(cp)) current += cps[i];
      else if (current) { if (Array.from(current).length >= 2 && Array.from(current).length <= 64 && out.indexOf(current) < 0) out.push(current); current = ""; }
    }
    if (current && Array.from(current).length >= 2 && Array.from(current).length <= 64 && out.indexOf(current) < 0) out.push(current);
    return out;
  }

  // Synchronous SHA-256 fallback for Safari installations without SubtleCrypto.
  function sha256Hex(text) {
    var bytes = unescape(encodeURIComponent(text)), words = [], bitLength = bytes.length * 8, i;
    for (i = 0; i < bytes.length; i += 1) words[i >> 2] = (words[i >> 2] || 0) | (bytes.charCodeAt(i) << (24 - (i % 4) * 8));
    words[bitLength >> 5] = (words[bitLength >> 5] || 0) | (0x80 << (24 - bitLength % 32));
    words[((bitLength + 64 >> 9) << 4) + 15] = bitLength;
    var k = [], primes = [], candidate = 2, n, isPrime, h = [], rootN, w = new Array(64), a,b,c,d,e,f,g,hh,t1,t2;
    while (k.length < 64) {
      isPrime = true;
      for (n = 2; n * n <= candidate; n += 1) if (candidate % n === 0) { isPrime = false; break; }
      if (isPrime) { primes.push(candidate); rootN = Math.pow(candidate, 1 / 3); k.push((Math.floor((rootN % 1) * 0x100000000)) | 0); }
      candidate += 1;
    }
    for (i = 0; i < 8; i += 1) { rootN = Math.sqrt(primes[i]); h[i] = Math.floor((rootN % 1) * 0x100000000) | 0; }
    function rotr(x, nbits) { return (x >>> nbits) | (x << (32 - nbits)); }
    for (var offset = 0; offset < words.length; offset += 16) {
      for (i = 0; i < 16; i += 1) w[i] = words[offset + i] | 0;
      for (i = 16; i < 64; i += 1) { var s0 = rotr(w[i-15],7) ^ rotr(w[i-15],18) ^ (w[i-15] >>> 3); var s1 = rotr(w[i-2],17) ^ rotr(w[i-2],19) ^ (w[i-2] >>> 10); w[i] = (w[i-16] + s0 + w[i-7] + s1) | 0; }
      a=h[0];b=h[1];c=h[2];d=h[3];e=h[4];f=h[5];g=h[6];hh=h[7];
      for (i = 0; i < 64; i += 1) { var S1=rotr(e,6)^rotr(e,11)^rotr(e,25), ch=(e&f)^(~e&g); t1=(hh+S1+ch+k[i]+w[i])|0; var S0=rotr(a,2)^rotr(a,13)^rotr(a,22), maj=(a&b)^(a&c)^(b&c); t2=(S0+maj)|0; hh=g;g=f;f=e;e=(d+t1)|0;d=c;c=b;b=a;a=(t1+t2)|0; }
      h[0]=(h[0]+a)|0;h[1]=(h[1]+b)|0;h[2]=(h[2]+c)|0;h[3]=(h[3]+d)|0;h[4]=(h[4]+e)|0;h[5]=(h[5]+f)|0;h[6]=(h[6]+g)|0;h[7]=(h[7]+hh)|0;
    }
    return h.map(function (x) { return (x >>> 0).toString(16).padStart(8, "0"); }).join("");
  }
  function shaPrefix(token) {
    var subtle = typeof crypto !== "undefined" && crypto.subtle && typeof TextEncoder !== "undefined";
    if (subtle) return crypto.subtle.digest("SHA-256", new TextEncoder().encode(token)).then(function (buffer) {
      var arr = Array.prototype.slice.call(new Uint8Array(buffer));
      return arr.map(function (b) { return (b < 16 ? "0" : "") + b.toString(16); }).join("").slice(0, 2);
    });
    return Promise.resolve(sha256Hex(token).slice(0, 2));
  }

  function create(options) {
    options = options || {};
    var baseUrl = options.baseUrl || "./", mode = options.mode || "public";
    var fetcher = options.fetchImpl || (typeof fetch === "function" ? fetch.bind(typeof window !== "undefined" ? window : null) : null);
    if (!fetcher) throw new HubError("fetch_unavailable", "Fetch is unavailable");
    var currentManifest = null, currentRoot = null, generationRoots = {}, cache = {}, pending = [], active = 0, sessionGeneration = null, updateHandler = options.onUpdateAvailable || null, offlineMode = false, pendingUpdate = null;
    function absolute(path) {
      var base = baseUrl;
      if (base.charAt(base.length - 1) !== "/") base += "/";
      return base + path;
    }
    function enqueue(work) {
      return new Promise(function (resolve, reject) {
        pending.push({work: work, resolve: resolve, reject: reject});
        pump();
      });
    }
    function pump() {
      while (active < 4 && pending.length) {
        (function (job) {
          active += 1;
          Promise.resolve().then(job.work).then(job.resolve, job.reject).then(function () { active -= 1; pump(); }, function () { active -= 1; pump(); });
        }(pending.shift()));
      }
    }
    function localKey(url) { return absolute(url); }
    function cacheGet(url) {
      if (Object.prototype.hasOwnProperty.call(cache, url)) return Promise.resolve(cache[url]);
      if (mode !== "public" || typeof caches === "undefined" || !caches.open) return Promise.resolve(null);
      return caches.open(CACHE_NAME).then(function (store) { return store.match(localKey(url)); }).then(function (response) {
        return response ? response.json().then(function (value) { cache[url] = value; return value; }) : null;
      }).catch(function () { return null; });
    }
    function cachePut(url, value) {
      cache[url] = value;
      if (mode !== "public" || typeof caches === "undefined" || !caches.open || typeof Response === "undefined") return Promise.resolve();
      return caches.open(CACHE_NAME).then(function (store) {
        return store.put(localKey(url), new Response(JSON.stringify(value), {headers: {"Content-Type": "application/json"}}));
      }).catch(function () {});
    }
    function rawFetch(url, timeout, noCache) {
      return enqueue(function () {
        var controller = typeof AbortController !== "undefined" ? new AbortController() : null;
        var timedOut = false, timer;
        var init = {method: "GET", cache: mode === "private" ? "no-store" : (noCache ? "no-cache" : "default")};
        if (controller) init.signal = controller.signal;
        var request = fetcher(absolute(url), init).then(function (response) {
          if (!response || !response.ok) throw new HubError(response && response.status === 404 ? "unavailable" : "http_error", response && response.status === 404 ? "Record unavailable in this view" : "Request failed" + (response ? " (" + response.status + ")" : ""), response ? response.status : 0, url);
          return response.json().catch(function () { throw new HubError("invalid_json", "Invalid JSON response", response.status, url); });
        });
        var timeoutPromise = new Promise(function (_, reject) {
          timer = setTimeout(function () { timedOut = true; if (controller) controller.abort(); reject(new HubError("timeout", "Request timed out", 0, url)); }, timeout || 10000);
        });
        return Promise.race([request, timeoutPromise]).catch(function (err) {
          if (err instanceof HubError) throw err;
          throw new HubError(timedOut || controller && controller.signal.aborted ? "timeout" : "network_error", timedOut || controller && controller.signal.aborted ? "Request timed out" : "Network request failed", 0, url);
        }).then(function (value) { clearTimeout(timer); return value; }, function (err) { clearTimeout(timer); throw err; });
      });
    }
    function checkedFetch(url, schema, opts) {
      opts = opts || {};
      var requestedGeneration = opts.generation || sessionGeneration;
      var isManifest = url === "manifest.json";
      return rawFetch(url, isManifest ? 10000 : 10000, isManifest).then(function (value) {
        if (!value || value.schema_version !== 1) throw new HubError("schema_error", "Update required: unsupported data schema", 0, url);
        if (isManifest && mode && value.mode !== mode) throw new HubError("mode_mismatch", "Data mode does not match this workspace", 0, url);
        if (schema && !schema(value)) throw new HubError("payload_error", "Invalid projection payload", 0, url);
        if (isManifest) offlineMode = false;
        return cachePut(url, value).then(function () { return value; });
      }).catch(function (err) {
        if (err.code === "unavailable" || err.code === "http_error" || err.code === "schema_error" || err.code === "payload_error" || err.code === "mode_mismatch") throw err;
        return cacheGet(url).then(function (saved) {
          if (!saved) throw err;
          if (!saved || saved.schema_version !== 1) throw new HubError("schema_error", "Update required: unsupported saved data schema", 0, url);
          if (isManifest && mode && saved.mode !== mode) throw new HubError("mode_mismatch", "Saved data mode does not match this workspace", 0, url);
          if (schema && !schema(saved)) throw new HubError("payload_error", "Invalid saved projection payload", 0, url);
          offlineMode = true;
          return saved;
        });
      });
    }
    function requireManifest() { return currentManifest ? Promise.resolve(currentManifest) : loadManifest(); }
    function genFile(path, generation) {
      var manifest = currentManifest;
      if (!manifest) return Promise.reject(new HubError("manifest_required", "Load the manifest first"));
      var gen = generation || sessionGeneration || manifest.generation;
      var rootPath = generationRoots[gen] || (gen === manifest.generation ? manifest.root : null);
      if (!rootPath) return Promise.reject(new HubError("generation_mismatch", "Requested data generation is unavailable"));
      return checkedFetch(rootPath + path, function (value) { return value.schema_version === 1; }, {generation: gen}).catch(function (err) {
        if (err.code !== "unavailable") throw err;
        return loadManifest().then(function () {
          var retryRoot = generationRoots[gen];
          if (!retryRoot) throw err;
          return checkedFetch(retryRoot + path, function (value) { return value.schema_version === 1; }, {generation: gen});
        });
      });
    }
    function validateManifest(value) {
      return value && typeof value.generation === "string" && /^[a-f0-9]{64}$/.test(value.generation) &&
        typeof value.root === "string" && value.root === "g/" + value.generation + "/" &&
        (value.mode === "public" || value.mode === "private") && typeof value.published_at === "string" &&
        typeof value.source_revision === "string" && typeof value.exporter_version === "string" &&
        typeof value.policy_digest === "string";
    }
    function loadManifest(opts) {
      opts = opts || {};
      var previous = currentManifest;
      return checkedFetch("manifest.json", validateManifest, {}).then(function (manifest) {
        if (mode && manifest.mode !== mode) throw new HubError("mode_mismatch", "Data mode does not match this workspace");
        if (previous && previous.generation !== manifest.generation && !opts.activate) {
          generationRoots[manifest.generation] = manifest.root;
          pendingUpdate = manifest;
          if (updateHandler) updateHandler(manifest, previous);
          return previous;
        }
        currentManifest = manifest;
        currentRoot = absolute(manifest.root);
        generationRoots[manifest.generation] = manifest.root;
        pendingUpdate = null;
        if (!sessionGeneration || opts.activate) sessionGeneration = manifest.generation;
        return manifest;
      }).catch(function (err) {
        if (err.code === "network_error" || err.code === "timeout") return cacheGet("manifest.json").then(function (saved) {
          if (!saved || !validateManifest(saved) || mode && saved.mode !== mode) throw err;
          currentManifest = saved; currentRoot = absolute(saved.root); generationRoots[saved.generation] = saved.root; sessionGeneration = saved.generation;
          return saved;
        });
        throw err;
      });
    }
    function activateGeneration(manifest) {
      if (!validateManifest(manifest) || mode && manifest.mode !== mode) throw new HubError("manifest_error", "Invalid generation manifest");
      currentManifest = manifest; currentRoot = absolute(manifest.root); generationRoots[manifest.generation] = manifest.root; sessionGeneration = manifest.generation;
      return currentManifest;
    }
    function get(path) { return requireManifest().then(function () { return genFile(path); }); }
    function catalog() { return get("catalog.json"); }
    function aliases() { return get("aliases.json"); }
    function catalogIndex() { return get("records/catalog/index.json"); }
    function catalogPage(n) { if (!Number.isInteger(n) || n < 1) return Promise.reject(new HubError("invalid_page", "Invalid catalog page")); return get("records/catalog/" + n + ".json"); }
    function catalogPages() {
      return catalogIndex().then(function (index) { return Promise.all((index.pages || []).map(function (page) { return genFile(page.url); })); }).then(function (pages) {
        var items = [];
        pages.forEach(function (page) { items = items.concat(page.items || []); });
        return items;
      });
    }
    function recordMeta(id) { if (!UUID.test(id)) return Promise.reject(new HubError("invalid_id", "Invalid record ID")); return get("records/" + id + ".meta.json"); }
    function record(id, opts) { if (!UUID.test(id)) return Promise.reject(new HubError("invalid_id", "Invalid record ID")); return recordMeta(id).then(function (meta) { if (meta.detail_bytes > 262144 && !(opts && opts.force)) return {meta: meta, requiresConfirmation: true}; return get("records/" + id + ".json"); }); }
    function eventMeta(id) { if (!UUID.test(id)) return Promise.reject(new HubError("invalid_id", "Invalid event ID")); return get("events/" + id + ".meta.json"); }
    function event(id, opts) { if (!UUID.test(id)) return Promise.reject(new HubError("invalid_id", "Invalid event ID")); return eventMeta(id).then(function (meta) { if (meta.detail_bytes > 262144 && !(opts && opts.force)) return {meta: meta, requiresConfirmation: true}; return get("events/" + id + ".json"); }); }
    function historyIndex(id) { if (!UUID.test(id)) return Promise.reject(new HubError("invalid_id", "Invalid record ID")); return get("history/" + id + "/index.json"); }
    function historyPage(id, n) { if (!UUID.test(id) || !Number.isInteger(n) || n < 1) return Promise.reject(new HubError("invalid_page", "Invalid history page")); return get("history/" + id + "/" + n + ".json"); }
    function calendar(year) { if (year && typeof year === "object") year = year.year; if (!/^\d{4}$/.test(String(year))) return Promise.reject(new HubError("invalid_year", "Invalid year")); return get("calendar/" + year + ".json").catch(function (err) { if (err.code === "unavailable") return {schema_version: 1, year: Number(year), days: []}; throw err; }); }
    function dayIndex(date) { if (!validDate(date)) return Promise.reject(new HubError("invalid_date", "Invalid date")); return get("days/" + date + "/index.json").catch(function (err) { if (err.code === "unavailable") return {schema_version: 1, date: date, change_count: 0, record_count: 0, pages: []}; throw err; }); }
    function dayPage(date, n) { if (!validDate(date) || !Number.isInteger(n) || n < 1) return Promise.reject(new HubError("invalid_page", "Invalid day page")); return get("days/" + date + "/" + n + ".json"); }
    function reminders(month) { if (!MONTH.test(month)) return Promise.reject(new HubError("invalid_month", "Invalid month")); return get("reminders/" + month + ".json"); }

    function matches(record, filters) {
      filters = filters || {};
      if ((record.status === "deprecated" || record.status === "archived") && filters.archived !== "1" && filters.status !== "deprecated" && filters.status !== "archived") return false;
      if (filters.project && record.project_id !== filters.project) return false;
      if (filters.area && record.area !== filters.area && record.area.indexOf(filters.area.replace(/\/$/, "") + "/") !== 0) return false;
      if (filters.type && record.type !== filters.type) return false;
      if (filters.status && record.status !== filters.status) return false;
      if (filters.tag && (record.tags || []).indexOf(filters.tag) < 0) return false;
      return true;
    }
    function resolveRecords(filters) {
      return catalogPages().then(function (items) {
        var results = items.filter(function (item) { return matches(item, filters); });
        if ((filters && filters.sort) === "updated") results.sort(function (a, b) { return (b.updated_at || "").localeCompare(a.updated_at || "") || a.id.localeCompare(b.id); });
        else results.sort(function (a, b) { return (a.title || "").toLowerCase().localeCompare((b.title || "").toLowerCase()) || a.id.localeCompare(b.id); });
        return {items: results, total: results.length, record_count: results.length, pages: [{number: 1, count: results.length}], metadata: items};
      });
    }
    function search(query, filters) {
      filters = filters || {};
      var qTokens = tokens(query);
      if (qTokens.length > 8) return Promise.reject(new HubError("too_many_tokens", "Search supports at most eight distinct tokens"));
      var indexed;
      return Promise.all([get("search/manifest.json"), catalogPages()]).then(function (values) {
        indexed = {manifest: values[0], records: values[1]};
        if (!qTokens.length) return indexed;
        var descriptors = {};
        (indexed.manifest.shards || []).forEach(function (shard) { descriptors[shard.prefix] = shard.url; });
        return Promise.all(qTokens.map(shaPrefix)).then(function (prefixes) {
          var uniquePrefixes = prefixes.filter(function (prefix, index) { return prefixes.indexOf(prefix) === index; });
          return Promise.all(uniquePrefixes.map(function (prefix) { return descriptors[prefix] ? genFile(descriptors[prefix]) : {schema_version: 1, terms: {}}; })).then(function (shards) {
            var byPrefix = {}; uniquePrefixes.forEach(function (prefix, index) { byPrefix[prefix] = shards[index]; });
            indexed.shards = prefixes.map(function (prefix) { return byPrefix[prefix]; });
            return indexed;
          });
        });
      }).then(function (loaded) {
        var byId = {}, score = {}, set = null, i, postings, current, weights = {title: 8, tag: 4, description: 2, body: 1};
        loaded.records.forEach(function (item) { byId[item.id] = item; });
        if (qTokens.length) {
          qTokens.forEach(function (token, tokenIndex) {
            postings = (loaded.shards[tokenIndex].terms || {})[token] || []; current = {};
            postings.forEach(function (posting) {
              current[posting.record_id] = true;
              var best = 0; (posting.fields || []).forEach(function (field) { if (weights[field] > best) best = weights[field]; });
              score[posting.record_id] = (score[posting.record_id] || 0) + best;
            });
            if (set === null) set = current; else Object.keys(set).forEach(function (rid) { if (!current[rid]) delete set[rid]; });
          });
        }
        var candidates = set === null ? loaded.records.map(function (item) { return item.id; }) : Object.keys(set);
        var results = candidates.map(function (id) { return byId[id]; }).filter(function (item) { return item && matches(item, filters); });
        results.sort(function (a, b) { return a.id.localeCompare(b.id); });
        results.sort(function (a, b) { return (b.updated_at || "").localeCompare(a.updated_at || ""); });
        results.sort(function (a, b) { return (score[b.id] || 0) - (score[a.id] || 0); });
        return {items: results, total: results.length, record_count: results.length, pages: [{number: 1, count: results.length}], scores: score, tokens: qTokens, metadata: loaded.records};
      });
    }

    function diaryInitialRange(request) {
      request = request || {};
      var start = request.start, end = request.end, filters = request.filters || {};
      if (!validDate(start) || !validDate(end) || start > end) return Promise.reject(new HubError("invalid_range", "Invalid diary range"));
      var dates = [], cursor = start, generation = sessionGeneration;
      while (cursor <= end) { dates.push(cursor); cursor = shiftDays(cursor, 1); }
      return Promise.all(dates.map(function (date) {
        return dayIndex(date).then(function (index) { return {date: date, index: index}; })
          .catch(function (err) { return {date: date, index: {schema_version: 1, date: date, change_count: 0, record_count: 0, pages: []}, error: err}; });
      })).then(function (indexedDays) {
        var newest = null;
        indexedDays.forEach(function (day) { if (!day.error && day.index.pages && day.index.pages.length && (!newest || day.date > newest)) newest = day.date; });
        return Promise.all(indexedDays.map(function (day) {
          if (day.error || !day.index.pages || !day.index.pages.length || request.mode === "month" && day.date !== newest) return {date: day.date, index: day.index, items: [], error: day.error};
          return genFile(day.index.pages[0].url, generation).then(function (page) { return {date: day.date, index: day.index, items: page.items || []}; })
            .catch(function (err) { return {date: day.date, index: day.index, items: [], error: err}; });
        }));
      }).then(function (days) {
        var rows = [].concat.apply([], days.map(function (day) { return day.items; }));
        if (Object.keys(filters).some(function (key) { return !!filters[key]; })) rows = rows.filter(function (item) {
          if (filters.project && item.project_id !== filters.project) return false;
          if (filters.area && item.area !== filters.area && item.area.indexOf(filters.area.replace(/\/$/, "") + "/") !== 0) return false;
          if (filters.type && item.type !== filters.type || filters.status && item.status !== filters.status) return false;
          if (filters.tag && (item.tags || []).indexOf(filters.tag) < 0 || filters.action && item.action !== filters.action) return false;
          return true;
        });
        rows.sort(function (a, b) { return (b.recorded_at || "").localeCompare(a.recorded_at || "") || (b.sequence || 0) - (a.sequence || 0) || a.id.localeCompare(b.id); });
        return {items: rows, dayIndexes: days.map(function (day) { return {date: day.date, index: day.index, error: day.error || null}; }), dayErrors: days.filter(function (day) { return day.error; }).map(function (day) { return {date: day.date, error: day.error}; }), total_changes: null, total_records: null, countsExact: false};
      });
    }
    function diaryRange(request) {
      request = request || {};
      var start = request.start, end = request.end, filters = request.filters || {};
      if (!validDate(start) || !validDate(end) || start > end) return Promise.reject(new HubError("invalid_range", "Invalid diary range"));
      var dates = [], cursor = start;
      while (cursor <= end) { dates.push(cursor); cursor = shiftDays(cursor, 1); }
      var generation = sessionGeneration;
      return Promise.all(dates.map(function (date) {
        return dayIndex(date).then(function (index) { return Promise.all((index.pages || []).map(function (page) { return genFile(page.url, generation); })); }).then(function (pages) {
          var dayItems = []; pages.forEach(function (page) { dayItems = dayItems.concat(page.items || []); }); return {date: date, items: dayItems};
        }).catch(function (err) { if (err.code === "unavailable") return {date: date, items: []}; return {date: date, items: [], error: err}; });
      })).then(function (daily) {
        var items = [].concat.apply([], daily.map(function (day) { return day.items; })).filter(function (item) {
          if (filters.project && item.project_id !== filters.project) return false;
          if (filters.area && item.area !== filters.area && item.area.indexOf(filters.area.replace(/\/$/, "") + "/") !== 0) return false;
          if (filters.type && item.type !== filters.type) return false;
          if (filters.status && item.status !== filters.status) return false;
          if (filters.tag && (item.tags || []).indexOf(filters.tag) < 0) return false;
          if (filters.action && item.action !== filters.action) return false;
          return true;
        });
        items.sort(function (a, b) { return (b.recorded_at || "").localeCompare(a.recorded_at || "") || (b.sequence || 0) - (a.sequence || 0) || a.id.localeCompare(b.id); });
        var ids = {}; items.forEach(function (item) { ids[item.record_id] = true; });
        var dayErrors = daily.filter(function (day) { return day.error; }).map(function (day) { return {date: day.date, error: day.error}; });
        return {items: items, total_changes: dayErrors.length ? null : items.length, total_records: dayErrors.length ? null : Object.keys(ids).length, countsExact: dayErrors.length === 0, dayErrors: dayErrors};
      });
    }
    function projectCounts(projectId) {
      return catalogPages().then(function (items) {
        var counts = {draft: 0, stable: 0, completed: 0};
        items.forEach(function (item) { if (item.id !== projectId && item.project_id === projectId && counts[item.status] !== undefined) counts[item.status] += 1; });
        return counts;
      });
    }
    function today(now) {
      if (now && typeof now === "object" && !(now instanceof Date)) now = now.date;
      var date = now ? dateString(utcDate(now)) : new Date().toISOString().slice(0, 10);
      var upcomingEnd = shiftDays(date, 7);
      var months = [date.slice(0, 7), upcomingEnd.slice(0, 7)];
      months = months.filter(function (m, index) { return months.indexOf(m) === index; });
      return Promise.all([Promise.all(months.map(function (m) { return reminders(m).catch(function (err) { if (err.code === "unavailable") return {schema_version: 1, month: m, items: []}; throw err; }); })), catalogPages()]).then(function (values) {
        var reminderItems = [], records = values[1], reminderSeen = {};
        values[0].forEach(function (payload) { (payload.items || []).forEach(function (item) { if (!reminderSeen[item.id]) { reminderSeen[item.id] = true; reminderItems.push(item); } }); });
        var todayReminders = [], upcoming = [], seen = {};
        reminderItems.forEach(function (item) {
          if (item.status === "deprecated") return;
          if (item.start_date <= date && item.end_date >= date) { todayReminders.push(item); seen[item.id] = true; }
          else if (item.end_date >= shiftDays(date, 1) && item.start_date <= upcomingEnd && !seen[item.id]) upcoming.push(item);
        });
        records = records.filter(function (item) { return item.status !== "deprecated"; });
        records.sort(function (a, b) { return (b.updated_at || "").localeCompare(a.updated_at || "") || a.id.localeCompare(b.id); });
        return {date: date, today: todayReminders, upcoming: upcoming, recently_updated: records.slice(0, 10)};
      });
    }
    function status() { return {manifest: currentManifest, generation: sessionGeneration, mode: mode, root: currentRoot, offline: offlineMode, updateAvailable: pendingUpdate}; }
    return {
      loadManifest: loadManifest, activateGeneration: activateGeneration, setUpdateHandler: function (fn) { updateHandler = fn; }, status: status,
      catalog: catalog, catalogIndex: catalogIndex, catalogPage: catalogPage, catalogPages: catalogPages, catalogRecords: catalogPages, aliases: aliases, recordMeta: recordMeta, record: record,
      eventMeta: eventMeta, event: event, historyIndex: historyIndex, historyPage: historyPage,
      calendar: calendar, dayIndex: dayIndex, dayPage: dayPage, reminders: reminders,
      search: search, resolveRecords: resolveRecords, diaryInitialRange: diaryInitialRange, diaryRange: diaryRange, projectCounts: projectCounts, today: today, get: get,
      loadMore: function (result, count) { count = count || 50; return (result.items || []).slice(0, count); },
      paginate: function (items, page, size) { size = size || 50; page = Math.max(0, page || 0); return (items || []).slice(page * size, (page + 1) * size); }
    };
  }

  return {
    create: create, Error: HubError, parseRoute: parseRoute, serializeRoute: serializeRoute,
    validDate: validDate, mondayStart: mondayStart, shiftDays: shiftDays, shiftMonth: shiftMonth,
    monthBounds: monthBounds, tokens: tokens, sha256Hex: sha256Hex, UUID: UUID
  };
}));
