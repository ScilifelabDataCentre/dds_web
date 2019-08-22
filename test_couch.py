<table class="table table-responsive table-hover">
<thead>
<tr>
<th>Project ID</th>
<th>Project</th>
<th>Order Date</th>
<th>Status</th>
</tr>
</thead>
{% if projects != {} %}
<tbody>
{% for proj in projects %}
{{ proj }}
{{ projects[proj] }}<br>
  <tr data-toggle="collapse" id="{{proj}}" data-target=".{{proj}}" aria-expanded="false" aria-controls="{{proj}}">
    <td>{{ proj }}</td>
    <td>{{ projects[proj]['name'] }}</td>
    <td>{{ projects[proj]['order_date'] }}</td>
    <td>{{ projects[proj]['status'] }}</td>
    <td>
      <button class="btn btn-default btn-sm">Info</button>
    </td>
    <td>
      <button class="btn btn-default btn-sm" type="submit" id="viewfiles" name="viewfiles">View Project</button>
    </td>
  </tr>

  <tr class="collapse {{proj}}">
    <td>
      <div>
        fgdfgdgd
      </div>
    </td>
  </tr>

{% end %}
</tbody>
{% end %}

</table>
