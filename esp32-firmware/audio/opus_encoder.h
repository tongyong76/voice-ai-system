#ifndef OPUS_ENCODER_H
#define OPUS_ENCODER_H

#include "esp_err.h"
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Initialize Opus encoder
 *
 * @return esp_err_t ESP_OK on success
 */
esp_err_t opus_encoder_init(void);

/**
 * @brief Encode PCM audio to Opus
 *
 * @param pcm_data Input PCM audio (16-bit signed)
 * @param pcm_samples Number of PCM samples
 * @param opus_buffer Output buffer for Opus data
 * @param opus_buffer_size Size of output buffer
 * @param opus_size Actual size of encoded Opus data
 * @return esp_err_t ESP_OK on success
 */
esp_err_t opus_encoder_encode(
    const int16_t *pcm_data,
    size_t pcm_samples,
    uint8_t *opus_buffer,
    size_t opus_buffer_size,
    size_t *opus_size
);

/**
 * @brief Deinitialize Opus encoder
 *
 * @return esp_err_t ESP_OK on success
 */
esp_err_t opus_encoder_deinit(void);

#ifdef __cplusplus
}
#endif

#endif // OPUS_ENCODER_H
