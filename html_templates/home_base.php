<!DOCTYPE html>

<html>
    <head>
        <title>Data Delivery Portal</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        
		<link rel="stylesheet" type="text/css"
			  href="https://code.jquery.com/ui/1.11.4/themes/smoothness/jquery-ui.css">
		<link rel="stylesheet" type="text/css"
			  href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css">
		<link rel="stylesheet" type="text/css"
			  href="https://cdn.datatables.net/1.10.11/css/dataTables.bootstrap.min.css">

        <!-- defer: script will not run until page has loaded -->
        <script defer src="https://cdn.datatables.net/1.10.11/js/jquery.dataTables.min.js"></script>
		<script defer src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js"></script>
		<script defer src="https://cdn.datatables.net/1.10.11/js/dataTables.bootstrap.min.js"></script>
        
        <style type="text/css">
            body {
                padding: 10px;
            }
            
            div.body_container {
                
            }
            
            div.header {
                height: 80px;
                width: 100%;
                text-align: center;
                vertical-align: middle;
                line-height: 80px;  
                background-color: #8ee27f;
                border-radius: 40px;
                font-family: 'Book Antiqua';
                font-size: 36px;
            }
            
            div.arch {
                height: 80px;
                width: 40px;
                background-color: #ffffff;
                border-radius: 0px 40px 40px 0px;
                float: left;
            }
            
            img.head_logo {
                height: 80px;
                width: 240px;
                float: left;
            }
            
			div.login-container{
				width: 50%;
				max-width: 700px;
			}
        </style>
    </head>
    <body>
        <div>
        <img class="head_logo" src="{{ static_url('data_centre_logo.png') }}">
        <div class="arch"></div>
        <div class="header"> Data delivery portal </div>
        <br>
        <br>
        <br>
        
    {% block content %}
    <div class="container">
		<div class="container login-container">
			<div class="panel panel-default">
				<div class="panel-heading text-center">
					<span class="glyphicon glyphicon-user"></span>
					Sign In
				</div>
				<div class="panel-body">
					<form action="{{ reverse_url('user') }}" role="form" method="post">
                        {% module xsrf_form_html() %}
						<div class="form-group">
							<label for="user_email">Email</label>
							<input type="text" class="form-control" name="user_email" id="user_email"
								   placeholder="User account email address">
						</div>
						<div class="form-group">
							<label for="password">Password</label>
							<input type="password" class="form-control" name="password" id="password">
						</div>
						<div class="form-group">
							<button type="submit" class="btn btn-info btn-block">
								<span class="glyphicon glyphicon-log-in"></span>
								Login
							</button>

						</div>
					</form>
				</div>
			</div>
		</div>
    </div>
    {% end %}

    </body>
</html>