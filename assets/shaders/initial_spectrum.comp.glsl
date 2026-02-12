/*
 * initial_spectrum.comp.glsl
 *
 * Author: storro
 * Date: 2026/02/11
 * Description: Generates the initial ocean spectrum (Tessendorf-style)
 *              Writes one float per texel (R32F), representing the wave amplitude h0(k)
 */

#version 430

#define COMPUTE_WORK_GROUP_DIM 32
#define PI 3.14159265359

layout (local_size_x = COMPUTE_WORK_GROUP_DIM, local_size_y = COMPUTE_WORK_GROUP_DIM) in;

// IMPORTANT: Panda3D binds image uniforms via set_shader_input
// The texture must use a *sized* format (eg. Texture.F_r32)
uniform writeonly image2D u_initial_spectrum;

uniform int u_resolution;
uniform int u_ocean_size;
uniform vec2 u_wind;

const float g = 9.81;
const float k_m = 370.0;
const float c_m = 0.23;

float omega(float k)
{
    return sqrt(g * k * (1.0 + ((k * k) / (k_m * k_m))));
}

float square(float x) {
    return x * x;
}

void main()
{
    ivec2 pixel_coord = ivec2(gl_GlobalInvocationID.xy);
    if (pixel_coord.x >= u_resolution || pixel_coord.y >= u_resolution) {
        return;
    }

    float half_res = 0.5 * float(u_resolution);

    float n = (float(pixel_coord.x) < half_res) ? float(pixel_coord.x) : float(pixel_coord.x) - float(u_resolution);
    float m = (float(pixel_coord.y) < half_res) ? float(pixel_coord.y) : float(pixel_coord.y) - float(u_resolution);

    vec2 wave_vector = (2.0 * PI * vec2(n, m)) / float(u_ocean_size);
    float k = length(wave_vector);

    // Avoid NaNs in normalize/divide paths.
    float wind_speed = length(u_wind);
    if (k < 1e-6 || wind_speed < 1e-6) {
        imageStore(u_initial_spectrum, pixel_coord, vec4(0.0, 0.0, 0.0, 0.0));
        return;
    }

    float omega_param = 0.84;
    float k_p = g * square(omega_param / wind_speed);

    float c = omega(k) / k;
    float c_p = omega(k_p) / k_p;

    float l_pm = exp(-1.25 * square(k_p / k));
    float gamma_peak = 1.7;
    float sigma = 0.08 * (1.0 + 4.0 * pow(omega_param, -3.0));
    float gamma_r = exp(-square(sqrt(k / k_p) - 1.0) / (2.0 * square(sigma)));
    float j_p = pow(gamma_peak, gamma_r);
    float f_p = l_pm * j_p * exp(-omega_param / sqrt(10.0) * (sqrt(k / k_p) - 1.0));
    float alpha_p = 0.006 * sqrt(omega_param);
    float b_l = 0.5 * alpha_p * c_p / c * f_p;

    float z_0 = 0.000037 * square(wind_speed) / g * pow(wind_speed / c_p, 0.9);
    float u_star = 0.41 * wind_speed / log(10.0 / z_0);
    float alpha_m = 0.01 * ((u_star < c_m) ? (1.0 + log(u_star / c_m)) : (1.0 + 3.0 * log(u_star / c_m)));
    float f_m = exp(-0.25 * square(k / k_m - 1.0));
    float b_h = 0.5 * alpha_m * c_m / c * f_m * l_pm;

    float a_0 = log(2.0) / 4.0;
    float a_m = 0.13 * u_star / c_m;
    float delta = tanh(a_0 + 4.0 * pow(c / c_p, 2.5) + a_m * pow(c_m / c, 2.5));

    float cos_phi = dot(normalize(u_wind), normalize(wave_vector));

    float s = (1.0 / (2.0 * PI)) * pow(k, -4.0) * (b_l + b_h) * (1.0 + delta * (2.0 * cos_phi * cos_phi - 1.0));

    float d_k = 2.0 * PI / float(u_ocean_size);
    float h = sqrt(max(s, 0.0) / 2.0) * d_k;

    imageStore(u_initial_spectrum, pixel_coord, vec4(h, 0.0, 0.0, 0.0));
}
