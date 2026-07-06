#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include "esp_err.h"
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Initialize Wi-Fi manager
 *
 * @return esp_err_t ESP_OK on success
 */
esp_err_t wifi_manager_init(void);

/**
 * @brief Check if Wi-Fi is connected
 *
 * @return true if connected, false otherwise
 */
bool wifi_manager_is_connected(void);

/**
 * @brief Connect to Wi-Fi network
 *
 * @param ssid Wi-Fi SSID
 * @param password Wi-Fi password
 * @return esp_err_t ESP_OK on success
 */
esp_err_t wifi_manager_connect(const char *ssid, const char *password);

/**
 * @brief Disconnect from Wi-Fi
 *
 * @return esp_err_t ESP_OK on success
 */
esp_err_t wifi_manager_disconnect(void);

#ifdef __cplusplus
}
#endif

#endif // WIFI_MANAGER_H
