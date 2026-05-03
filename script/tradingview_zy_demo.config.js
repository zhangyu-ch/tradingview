module.exports = {
    apps: [{
        name: "tradingview_zy_demo",
        cwd: "./../web/tradingview_zy_chart",
        script: "/root/miniconda3/envs/tradingview_zy/bin/python3 app.py nobrowser",
        error_file: "./logs/web-error.log",
        out_file: "./logs/web-out.log",
    }
    ]
}
