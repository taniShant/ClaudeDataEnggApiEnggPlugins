# WireMock Test Data

Some BUK projects use WireMock for integration testing. Sample MTS EDO-level request/response JSON may live in:

- **Response bodies:** `src/test/resources/__files/<domain>/`
- **Mappings:** `src/test/resources/mappings/<domain>/` (URL pattern to response body routing)
- **Bridge class:** `WiremockServerCIRestConnectorImpl` intercepts service delegate calls and routes to WireMock

## Usage in Documentation

If WireMock test data exists, use it to build realistic sample request/response JSON for per-service docs. The response body files contain actual JSON payloads that map directly to the response EDOs.

If no WireMock test data exists, build sample request/response JSON from DTO field names and reasonable placeholder values.
