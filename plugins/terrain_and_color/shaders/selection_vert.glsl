#version 330

uniform mat4 projectionMatrix;
uniform mat4 modelViewMatrix;
uniform vec4 color;
uniform float heightFactor;

in vec3 position;

out vec4 finalColor;

void main() {
	vec3 scale = vec3(1., heightFactor, 1.);
	vec4 eyePosition = modelViewMatrix * vec4(position * scale, 1.0);
    gl_Position = projectionMatrix * eyePosition;
    finalColor = color;
}
