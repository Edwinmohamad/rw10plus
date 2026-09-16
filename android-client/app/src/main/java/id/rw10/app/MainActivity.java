package id.rw10.app;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.webkit.CookieManager;
import android.webkit.SslErrorHandler;
import android.net.http.SslError;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

public class MainActivity extends Activity {
    private WebView webView;
    private LinearLayout errorView;
    private final Uri serverUri = Uri.parse(BuildConfig.SERVER_URL);

    @SuppressLint("SetJavaScriptEnabled")
    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.rgb(245,247,251));
        getWindow().setNavigationBarColor(Color.rgb(245,247,251));
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR | View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.rgb(245,247,251));

        webView = new WebView(this);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setMediaPlaybackRequiresUserGesture(true);
        if (android.os.Build.VERSION.SDK_INT >= 26) settings.setSafeBrowsingEnabled(true);
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, false);
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG);
        webView.setWebViewClient(new SecureClient());

        errorView = buildErrorView();
        root.addView(webView, new LinearLayout.LayoutParams(-1, 0, 1));
        root.addView(errorView, new LinearLayout.LayoutParams(-1, -1));
        setContentView(root);
        loadApp();
    }

    private void loadApp() { errorView.setVisibility(View.GONE); webView.setVisibility(View.VISIBLE); webView.loadUrl(BuildConfig.SERVER_URL); }

    private LinearLayout buildErrorView() {
        LinearLayout panel = new LinearLayout(this); panel.setOrientation(LinearLayout.VERTICAL); panel.setGravity(android.view.Gravity.CENTER); panel.setPadding(42,42,42,42);
        TextView mark = new TextView(this); mark.setText("RW10+"); mark.setTextColor(Color.rgb(37,87,214)); mark.setTextSize(34); mark.setTypeface(null, android.graphics.Typeface.BOLD); panel.addView(mark);
        TextView title = new TextView(this); title.setText("Server RW10+ belum terhubung"); title.setTextColor(Color.rgb(32,39,34)); title.setTextSize(19); title.setGravity(android.view.Gravity.CENTER); title.setPadding(0,30,0,8); panel.addView(title);
        TextView info = new TextView(this); info.setText("Pastikan HP terhubung ke jaringan RW10 dan server 192.168.100.50 aktif."); info.setTextColor(Color.rgb(108,117,111)); info.setTextSize(14); info.setGravity(android.view.Gravity.CENTER); info.setPadding(0,0,0,24); panel.addView(info);
        Button retry = new Button(this); retry.setText("Coba lagi"); retry.setTextColor(Color.WHITE); retry.setBackgroundColor(Color.rgb(37,87,214)); retry.setOnClickListener(v -> loadApp()); panel.addView(retry, new LinearLayout.LayoutParams(-1,56)); panel.setVisibility(View.GONE); return panel;
    }

    private boolean sameServer(Uri uri) { return uri != null && serverUri.getHost() != null && serverUri.getHost().equalsIgnoreCase(uri.getHost()) && serverUri.getPort() == uri.getPort(); }
    private void showError() { webView.setVisibility(View.GONE); errorView.setVisibility(View.VISIBLE); }

    private final class SecureClient extends WebViewClient {
        @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
            Uri uri=request.getUrl(); if (sameServer(uri)) return false;
            if ("http".equals(uri.getScheme()) || "https".equals(uri.getScheme())) startActivity(new Intent(Intent.ACTION_VIEW,uri));
            return true;
        }
        @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) { if (request.isForMainFrame()) showError(); }
        @Override public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) { handler.cancel(); showError(); }
    }

    @Override public void onBackPressed() {
        if (webView.getVisibility()==View.VISIBLE) {
            webView.evaluateJavascript("window.rw10Back ? String(window.rw10Back()) : 'false'", value -> {
                if (!"\"true\"".equals(value) && !"true".equals(value)) {
                    if (webView.canGoBack()) webView.goBack(); else finish();
                }
            });
        } else super.onBackPressed();
    }
    @Override protected void onDestroy() { if(webView!=null){ webView.stopLoading(); webView.destroy(); } super.onDestroy(); }
}
