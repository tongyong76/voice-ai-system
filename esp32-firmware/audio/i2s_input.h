#ifndef I2S_INPUT_H
#define I2S_INPUT_H

#include "esp_err.h"
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Initialize I2S input for microphone
 *
 * @return esp_err_t ESP_OK on success
 */
esp_err_t i2s_input_init(void);

/**
 * @brief Read audio data from I2S input
 *
 * @param buffer Buffer to store audio data
 * @param buffer_size Size of buffer in bytes
 * @param bytes_read Number of bytes actually read
 * @param timeout_ms Timeout in milliseconds
 * @return esp_err_t ESP_OK on success
 */
esp_err_t i2s_input_read(uint8_t *buffer, size_t buffer_size, size_t *bytes_read, uint32_t timeout_ms);

/**
 * @brief Deinitialize I2S input
 *
 * @return esp_err_t ESP_OK on success
 */
esp_err_t i2s_input_deinit(void);

#ifdef __cplusplus
}
#endif

#endif // I2S_INPUT_H
