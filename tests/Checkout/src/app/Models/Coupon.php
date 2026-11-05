<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Coupon extends Model
{
    protected $fillable = ['code', 'percent', 'active', 'expires_at'];

    protected $casts = [
        'active' => 'bool',
        'expires_at' => 'datetime',
    ];

    public function isRedeemable(): bool
    {
        return $this->active && $this->expires_at !== null && $this->expires_at->isFuture();
    }
}
