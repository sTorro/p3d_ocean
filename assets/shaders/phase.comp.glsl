/*
 * phase.comp.glsl
 *
 * Author: storro
 * Date: 2026/02/11
 * Description: Compute shader for advancing ocean wave phases through time (ping-pong)
 */

#version 430

#define PI 3.14159265359

layout (local_size_x = 32, local_size_y = 32) in;

layout(r32f) uniform readonly image2D u_phases;         // R32F
layout(r32f) uniform writeonly image2D u_delta_phases;  // R32F

uniform float u_delta_time;
uniform int u_ocean_size;
uniform int u_resolution;

const float g = 9.81;
const float KM = 370.0;

float omega(float k)
{
    // Deep water dispersion with a small high-frequency correction.
    return sqrt(g * k * (1.0 + (k * k) / (KM * KM)));
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

    float phase = imageLoad(u_phases, pixel_coord).r;

    // For k=0, omega(k)=0 so phase stays constant.
    float delta_phase = omega(k) * u_delta_time;
    phase = mod(phase + delta_phase, 2.0 * PI);

    imageStore(u_delta_phases, pixel_coord, vec4(phase, 0.0, 0.0, 0.0));
}
