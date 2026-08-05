package de.onyxbits.textfiction.lloyd;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.Charset;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Embedded HTTP API so Lloyd can play TextFiction autonomously.
 *
 * GET  /status   → agent health
 * GET  /state    → story text + status + waiting_for_command
 * POST /command  → Lloyd submits a player command
 * POST /reset    → clear buffers
 *
 * Default port 8765. Lloyd connects like any HTTP client.
 */
public final class LloydAgentApi implements Runnable {

	public static final int DEFAULT_PORT = 8765;

	private final int port;
	private final AtomicReference<String> lastText = new AtomicReference<String>("");
	private final AtomicReference<String> statusLine = new AtomicReference<String>("");
	private final AtomicReference<Boolean> waitingCmd = new AtomicReference<Boolean>(false);
	private final LinkedBlockingQueue<String> commandQueue = new LinkedBlockingQueue<String>();
	private volatile boolean running = true;
	private Thread thread;
	private ServerSocket server;

	public interface CommandSink {
		void submitCommand(String command);
	}

	private volatile CommandSink sink;

	public LloydAgentApi(int port) {
		this.port = port;
	}

	public void setCommandSink(CommandSink sink) {
		this.sink = sink;
	}

	public void publishState(String mainText, String status, boolean waitingForCommand) {
		if (mainText != null) lastText.set(mainText);
		if (status != null) statusLine.set(status);
		waitingCmd.set(waitingForCommand);
	}

	public void start() {
		if (thread != null) return;
		thread = new Thread(this, "lloyd-agent-api");
		thread.setDaemon(true);
		thread.start();
	}

	public void stop() {
		running = false;
		try { if (server != null) server.close(); } catch (IOException ignored) {}
	}

	public String pollCommand() {
		return commandQueue.poll();
	}

	@Override
	public void run() {
		try {
			server = new ServerSocket(port);
			server.setReuseAddress(true);
			while (running) {
				Socket client = server.accept();
				handle(client);
			}
		} catch (IOException e) {
			if (running) android.util.Log.w("LloydAgentApi", "server stopped: " + e.getMessage());
		}
	}

	private void handle(Socket client) {
		BufferedReader in = null;
		OutputStream out = null;
		try {
			client.setSoTimeout(15000);
			in = new BufferedReader(new InputStreamReader(client.getInputStream(), Charset.forName("UTF-8")));
			out = client.getOutputStream();
			String requestLine = in.readLine();
			if (requestLine == null) return;
			String[] parts = requestLine.split(" ");
			String method = parts.length > 0 ? parts[0] : "GET";
			String path = parts.length > 1 ? parts[1] : "/";
			if (path.contains("?")) path = path.substring(0, path.indexOf('?'));

			int contentLength = 0;
			String line;
			while ((line = in.readLine()) != null && line.length() > 0) {
				if (line.toLowerCase().startsWith("content-length:")) {
					try { contentLength = Integer.parseInt(line.substring(15).trim()); } catch (NumberFormatException ignored) {}
				}
			}
			String body = "";
			if (contentLength > 0) {
				char[] buf = new char[contentLength];
				int got = 0;
				while (got < contentLength) {
					int n = in.read(buf, got, contentLength - got);
					if (n < 0) break;
					got += n;
				}
				body = new String(buf, 0, got);
			}

			if ("GET".equals(method) && ("/state".equals(path) || "/".equals(path))) {
				writeResponse(out, 200, "application/json", stateJson());
			} else if ("GET".equals(method) && "/status".equals(path)) {
				writeResponse(out, 200, "application/json",
					"{\"ok\":true,\"agent\":\"lloyd-textfiction\",\"port\":" + port + ",\"waiting\":" + waitingCmd.get() + "}");
			} else if ("POST".equals(method) && "/command".equals(path)) {
				String cmd = extractCommand(body);
				if (cmd.length() == 0) {
					writeResponse(out, 400, "application/json", "{\"error\":\"empty command\"}");
				} else {
					commandQueue.offer(cmd);
					CommandSink s = sink;
					if (s != null) s.submitCommand(cmd);
					writeResponse(out, 200, "application/json", "{\"ok\":true,\"command\":" + jsonString(cmd) + "}");
				}
			} else if ("POST".equals(method) && "/reset".equals(path)) {
				lastText.set("");
				statusLine.set("");
				commandQueue.clear();
				writeResponse(out, 200, "application/json", "{\"ok\":true,\"reset\":true}");
			} else {
				writeResponse(out, 404, "application/json", "{\"error\":\"not found\"}");
			}
		} catch (Exception e) {
			try {
				if (out != null) writeResponse(out, 500, "application/json", "{\"error\":" + jsonString(String.valueOf(e.getMessage())) + "}");
			} catch (Exception ignored) {}
		} finally {
			try { client.close(); } catch (IOException ignored) {}
		}
	}

	private String stateJson() {
		return "{\"text\":" + jsonString(lastText.get()) + ",\"status_line\":"
				+ jsonString(statusLine.get()) + ",\"waiting_for_command\":" + waitingCmd.get() + "}";
	}

	private static String extractCommand(String body) {
		if (body == null) return "";
		body = body.trim();
		if (body.startsWith("{")) {
			int i = body.indexOf("\"command\"");
			if (i >= 0) {
				int c = body.indexOf(':', i);
				int q1 = body.indexOf('"', c + 1);
				int q2 = body.indexOf('"', q1 + 1);
				if (q1 >= 0 && q2 > q1) return body.substring(q1 + 1, q2).trim();
			}
			return "";
		}
		return body.replace("\r", "").replace("\n", "").trim();
	}

	private static String jsonString(String s) {
		if (s == null) s = "";
		StringBuilder sb = new StringBuilder("\"");
		for (int i = 0; i < s.length(); i++) {
			char ch = s.charAt(i);
			switch (ch) {
			case '"': sb.append("\\\""); break;
			case '\\': sb.append("\\\\"); break;
			case '\n': sb.append("\\n"); break;
			case '\r': sb.append("\\r"); break;
			case '\t': sb.append("\\t"); break;
			default:
				if (ch < 0x20) sb.append(String.format("\\u%04x", (int) ch));
				else sb.append(ch);
			}
		}
		sb.append('"');
		return sb.toString();
	}

	private static void writeResponse(OutputStream out, int code, String ctype, String body) throws IOException {
		byte[] data = body.getBytes("UTF-8");
		String reason = code == 200 ? "OK" : (code == 404 ? "Not Found" : "Error");
		String headers = "HTTP/1.1 " + code + " " + reason + "\r\nContent-Type: " + ctype
				+ "; charset=utf-8\r\nContent-Length: " + data.length + "\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n";
		out.write(headers.getBytes("UTF-8"));
		out.write(data);
		out.flush();
	}
}
