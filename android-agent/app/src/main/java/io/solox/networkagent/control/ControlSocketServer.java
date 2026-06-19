package io.solox.networkagent.control;

import android.net.LocalServerSocket;
import android.net.LocalSocket;
import android.util.Log;

import java.io.BufferedReader;
import java.io.Closeable;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;

import io.solox.networkagent.runtime.AgentRuntime;

public final class ControlSocketServer implements Closeable {
    public static final String SOCKET_NAME = "solox.networkagent.control";
    public static final int MAX_REQUEST_BYTES = 1024 * 1024;
    private static final int REQUEST_TIMEOUT_MS = 5000;

    private final CommandDispatcher dispatcher;
    private LocalServerSocket serverSocket;
    private Thread thread;
    private volatile boolean running;

    public ControlSocketServer(CommandDispatcher dispatcher) {
        this.dispatcher = dispatcher;
    }

    public synchronized void start() throws IOException {
        if (running) {
            return;
        }
        try {
            serverSocket = new LocalServerSocket(SOCKET_NAME);
        } catch (IOException exc) {
            AgentRuntime.error("socket", "control socket start failed");
            throw exc;
        }
        running = true;
        thread = new Thread(this::acceptLoop, "solox-agent-control");
        thread.start();
        AgentRuntime.info("socket", "started " + SOCKET_NAME);
    }

    private void acceptLoop() {
        while (running) {
            try {
                LocalSocket socket = serverSocket.accept();
                Thread handler = new Thread(() -> handle(socket), "solox-agent-control-client");
                handler.start();
            } catch (IOException exc) {
                if (running) {
                    AgentRuntime.warn("socket", "control socket accept failed");
                    Log.w("SoloXAgent", "control socket accept failed", exc);
                }
            }
        }
    }

    private void handle(LocalSocket socket) {
        try (LocalSocket closeable = socket;
             BufferedReader reader = new BufferedReader(new InputStreamReader(closeable.getInputStream(), StandardCharsets.UTF_8));
             OutputStreamWriter writer = new OutputStreamWriter(closeable.getOutputStream(), StandardCharsets.UTF_8)) {
            closeable.setSoTimeout(REQUEST_TIMEOUT_MS);
            String request = readCappedLine(reader);
            AgentRuntime.info("socket", "request received");
            String response = dispatcher.dispatch(request, System.currentTimeMillis());
            writer.write(response);
            writer.write('\n');
            writer.flush();
        } catch (IOException exc) {
            AgentRuntime.warn("socket", "control socket request failed");
            Log.w("SoloXAgent", "control socket request failed", exc);
        }
    }

    private static String readCappedLine(BufferedReader reader) throws IOException {
        StringBuilder builder = new StringBuilder();
        int current;
        int bytes = 0;
        while ((current = reader.read()) != -1) {
            if (current == '\n') {
                return builder.toString();
            }
            bytes += String.valueOf((char) current).getBytes(StandardCharsets.UTF_8).length;
            if (bytes > MAX_REQUEST_BYTES) {
                throw new IOException("request exceeds limit");
            }
            builder.append((char) current);
        }
        throw new IOException("request is not newline terminated");
    }

    @Override
    public synchronized void close() throws IOException {
        running = false;
        if (serverSocket != null) {
            serverSocket.close();
            serverSocket = null;
        }
        AgentRuntime.info("socket", "stopped");
    }
}
