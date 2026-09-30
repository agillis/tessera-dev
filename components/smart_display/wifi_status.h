#pragma once
// Wi-Fi as the glass tells it (firmware 0.19.0). A screen that cannot reach its network can reach nobody to say so:
// no Home Assistant, no ESP Screens. So the screen says it itself, on the loading screen over everything, with what
// fixes it. A board with a hotspot (ESPHome's `ap:`, which starts some 90 seconds after the network is gone) names that
// hotspot and its password: join it with a phone and pick the right network on the page that opens. A board without
// one (4 MB of flash, no room for it) says to check the name and password and to install the screen again over USB.
// On the host (the preview and the tests) there is no Wi-Fi to lose, and nothing is ever shown.
#include <cstdint>
#include <string>
#if defined(USE_WIFI) && !defined(ESP_SCREEN_HOST)
#include "esphome/components/wifi/wifi_component.h"
#include "esphome/core/hal.h"
#endif

namespace wifi_status {

struct Problem {
  bool shown = false;
  bool hotspot = false;   // the board opens a hotspot, and it is up now
  std::string ssid, password;
};

// How long the network may be gone before a board without a hotspot says so: long enough for a router that restarts.
constexpr uint32_t NO_HOTSPOT_AFTER_MS = 60000;

inline Problem problem() {
  Problem p;
#if defined(USE_WIFI) && !defined(ESP_SCREEN_HOST)
  static uint32_t lost_at = 0;
  auto *wifi = esphome::wifi::global_wifi_component;
  if (wifi == nullptr || wifi->is_disabled()) return p;
  const uint32_t now = esphome::millis();
  if (wifi->is_connected()) { lost_at = 0; return p; }
  if (lost_at == 0) lost_at = now ? now : 1;
#ifdef USE_WIFI_AP
  // ESPHome has the hotspot's settings only on a board built with one (USE_WIFI_AP).
  if (wifi->has_ap()) {
    // Said once the hotspot is there to join, not before: until then the screen is still trying its network.
    if (!wifi->is_ap_active()) return p;
    auto ap = wifi->get_ap();
    p.shown = p.hotspot = true;
    p.ssid = std::string(ap.get_ssid().c_str(), ap.get_ssid().size());
    p.password = std::string(ap.get_password().c_str(), ap.get_password().size());
    return p;
  }
#endif
  p.shown = now - lost_at > NO_HOTSPOT_AFTER_MS;
#endif
  return p;
}

}  // namespace wifi_status
