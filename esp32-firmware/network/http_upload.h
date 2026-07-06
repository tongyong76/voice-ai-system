#ifndef HTTP_UPLOAD_H
#define HTTP_UPLOAD_H

#include "esp_err.h"
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Initialize HTTP upload module
 *
 * @return esp_err_t ESP_OK on success
 */
esp_err_t http_upload_init(void);

/**
 * @brief Add audio data to upload queue
 *
 * @param data Audio data buffer
 * @param size Size of data in bytes
 * @return esp_err_t ESP_OK on success
 */
esp_err_t http_upload_queue_add(const uint8_t *data, size_t size);

/**
 * @brief Process upload queue (upload when connected)
 *
 * @return esp_err_t ESP_OK on success
 */
esp_err_t http_upload_process_queue(void);

/**
 * @brief Set server URL for upload
 *
 * @param url Server URL (e.g., "http://192.168.1.100:8000")
 * @return esp_err_t ESP_OK on success
 */
esp_err_t http_upload_set_server(const char *url);

#ifdef __cplusplus
}
#endif

#endif // HTTP_UPLOAD_H
