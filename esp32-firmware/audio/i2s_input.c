#include "i2s_input.h"
#include "driver/i2s_std.h"
#include "esp_log.h"

static const char *TAG = "I2S_INPUT";

// I2S configuration for ReSpeaker Lite
#define I2S_NUM         (0)
#define I2S_BCK_PIN     (41)
#define I2S_WS_PIN      (42)
#define I2S_DATA_IN_PIN (2)

#define SAMPLE_RATE     (16000)
#define BITS_PER_SAMPLE (16)

static i2s_chan_handle_t rx_handle = NULL;

esp_err_t i2s_input_init(void)
{
    ESP_LOGI(TAG, "Initializing I2S input");

    // Configure I2S channel
    i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM, I2S_ROLE_MASTER);
    chan_cfg.auto_clear = true;

    esp_err_t ret = i2s_new_channel(&chan_cfg, NULL, &rx_handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to create I2S channel: %s", esp_err_to_name(ret));
        return ret;
    }

    // Configure I2S standard mode
    i2s_std_config_t std_cfg = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(SAMPLE_RATE),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .mclk = I2S_GPIO_UNUSED,
            .bclk = I2S_BCK_PIN,
            .ws = I2S_WS_PIN,
            .dout = I2S_GPIO_UNUSED,
            .din = I2S_DATA_IN_PIN,
            .invert_flags = {
                .mclk_inv = false,
                .bclk_inv = false,
                .ws_inv = false,
            },
        },
    };

    ret = i2s_channel_init_std_mode(rx_handle, &std_cfg);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to init I2S std mode: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = i2s_channel_enable(rx_handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to enable I2S channel: %s", esp_err_to_name(ret));
        return ret;
    }

    ESP_LOGI(TAG, "I2S input initialized successfully");
    return ESP_OK;
}

esp_err_t i2s_input_read(uint8_t *buffer, size_t buffer_size, size_t *bytes_read, uint32_t timeout_ms)
{
    if (rx_handle == NULL) {
        return ESP_ERR_INVALID_STATE;
    }

    return i2s_channel_read(rx_handle, buffer, buffer_size, bytes_read, timeout_ms);
}

esp_err_t i2s_input_deinit(void)
{
    if (rx_handle != NULL) {
        i2s_channel_disable(rx_handle);
        i2s_del_channel(rx_handle);
        rx_handle = NULL;
    }
    return ESP_OK;
}
